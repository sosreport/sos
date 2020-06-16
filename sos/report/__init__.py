# Copyright (C) 2006 Steve Conklin <sconklin@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import sys
import traceback
import os
import errno
import logging

from datetime import datetime
import glob
import sos.report.plugins
from sos.utilities import ImporterHelper, SoSTimeoutError
from shutil import rmtree
import hashlib
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import pdb

from sos import _sos as _
from sos import __version__
from sos.component import SoSComponent
import sos.policies
from sos.report.reporting import (Report, Section, Command, CopiedFile,
                                  CreatedFile, Alert, Note, PlainTextReport,
                                  JSONReport, HTMLReport)

# file system errors that should terminate a run
fatal_fs_errors = (errno.ENOSPC, errno.EROFS)


def _format_list(first_line, items, indent=False, sep=", "):
    lines = []
    line = first_line
    if indent:
        newline = len(first_line) * ' '
    else:
        newline = ""
    for item in items:
        if len(line) + len(item) + len(sep) > 72:
            lines.append(line)
            line = newline
        line = line + item + sep
    if line[-len(sep):] == sep:
        line = line[:-len(sep)]
    lines.append(line)
    return lines


def _format_since(date):
    """ This function will format --since arg to append 0s if enduser
    didn't. It's used in the _get_parser.
    This will also be a good place to add human readable and relative
    date parsing (like '2 days ago') in the future """
    return datetime.strptime('{:<014s}'.format(date), '%Y%m%d%H%M%S')


# valid modes for --chroot
chroot_modes = ["auto", "always", "never"]


class SoSReport(SoSComponent):
    """Run a set of commands and file collections and save them to a report for
    future analysis
    """

    desc = "Collect files and command output in an archive"

    arg_defaults = {
        'alloptions': False,
        'all_logs': False,
        'batch': False,
        'build': False,
        'case_id': '',
        'chroot': 'auto',
        'desc': '',
        'dry_run': False,
        'experimental': False,
        'enableplugins': [],
        'plugopts': [],
        'label': '',
        'list_plugins': False,
        'list_presets': False,
        'list_profiles': False,
        'log_size': 25,
        'noplugins': [],
        'noreport': False,
        'no_env_vars': False,
        'no_postproc': False,
        'note': '',
        'onlyplugins': [],
        'preset': 'auto',
        'plugin_timeout': 300,
        'profiles': [],
        'since': None,
        'verify': False,
        'compression_type': 'auto',
        'allow_system_changes': False,
        'upload': False,
        'upload_url': None,
        'upload_directory': None,
        'upload_user': None,
        'upload_pass': None,
        'add_preset': '',
        'del_preset': '',
        'encrypt_key': None,
        'encrypt_pass': None
    }

    def __init__(self, parser, args, cmdline):
        super(SoSReport, self).__init__(parser, args, cmdline)
        self.loaded_plugins = []
        self.skipped_plugins = []
        self.all_options = []
        self.env_vars = set()
        self.archive = None
        self._args = args
        self.sysroot = "/"
        self.preset = None

        self.print_header()
        self._set_debug()

        self._is_root = self.policy.is_root()

        # user specified command line preset
        if self.opts.preset != self.arg_defaults["preset"]:
            self.preset = self.policy.find_preset(self.opts.preset)
            if not self.preset:
                sys.stderr.write("Unknown preset: '%s'\n" % self.opts.preset)
                self.preset = self.policy.probe_preset()
                self.opts.list_presets = True

        # --preset=auto
        if not self.preset:
            self.preset = self.policy.probe_preset()
        # now merge preset options to self.opts
        self.opts.merge(self.preset.opts)

        self._set_directories()

        msg = "default"
        host_sysroot = self.policy.host_sysroot()
        # set alternate system root directory
        if self.opts.sysroot:
            msg = "cmdline"
            self.sysroot = self.opts.sysroot
        elif self.policy.in_container() and host_sysroot != os.sep:
            msg = "policy"
            self.sysroot = host_sysroot
        self.soslog.debug("set sysroot to '%s' (%s)" % (self.sysroot, msg))

        if self.opts.chroot not in chroot_modes:
            self.soslog.error("invalid chroot mode: %s" % self.opts.chroot)
            logging.shutdown()
            self.tempfile_util.clean()
            self._exit(1)

        self._get_hardware_devices()

    @classmethod
    def add_parser_options(cls, parser):
        parser.add_argument("-a", "--alloptions", action="store_true",
                            dest="alloptions", default=False,
                            help="enable all options for loaded plugins")
        parser.add_argument("--all-logs", action="store_true",
                            dest="all_logs", default=False,
                            help="collect all available logs regardless "
                                 "of size")
        parser.add_argument("--since", action="store",
                            dest="since", default=None,
                            type=_format_since,
                            help="Escapes archived files older than date. "
                                 "This will also affect --all-logs. "
                                 "Format: YYYYMMDD[HHMMSS]")
        parser.add_argument("--batch", action="store_true",
                            dest="batch", default=False,
                            help="batch mode - do not prompt interactively")
        parser.add_argument("--build", action="store_true",
                            dest="build", default=False,
                            help="preserve the temporary directory and do not "
                                 "package results")
        parser.add_argument("--case-id", action="store",
                            dest="case_id",
                            help="specify case identifier")
        parser.add_argument("-c", "--chroot", action="store", dest="chroot",
                            help="chroot executed commands to SYSROOT "
                                 "[auto, always, never] (default=auto)",
                            default='auto')
        parser.add_argument("--desc", "--description", type=str,
                            action="store", default="",
                            help="Description for a new preset",)
        parser.add_argument("--dry-run", action="store_true",
                            help="Run plugins but do not collect data")
        parser.add_argument("--experimental", action="store_true",
                            dest="experimental", default=False,
                            help="enable experimental plugins")
        parser.add_argument("-e", "--enable-plugins", action="extend",
                            dest="enableplugins", type=str,
                            help="enable these plugins", default=[])
        parser.add_argument("-k", "--plugin-option", action="extend",
                            dest="plugopts", type=str,
                            help="plugin options in plugname.option=value "
                                 "format (see -l)", default=[])
        parser.add_argument("--label", "--name", action="store", dest="label",
                            help="specify an additional report label")
        parser.add_argument("-l", "--list-plugins", action="store_true",
                            dest="list_plugins", default=False,
                            help="list plugins and available plugin options")
        parser.add_argument("--list-presets", action="store_true",
                            help="display a list of available presets")
        parser.add_argument("--list-profiles", action="store_true",
                            dest="list_profiles", default=False,
                            help="display a list of available profiles and "
                                 "plugins that they include")
        parser.add_argument("--log-size", action="store", dest="log_size",
                            type=int, default=25,
                            help="limit the size of collected logs (in MiB)")
        parser.add_argument("-n", "--skip-plugins", action="extend",
                            dest="noplugins", type=str,
                            help="disable these plugins", default=[])
        parser.add_argument("--no-report", action="store_true",
                            dest="noreport", default=False,
                            help="disable plaintext/HTML reporting")
        parser.add_argument("--no-env-vars", action="store_true",
                            dest="no_env_vars", default=False,
                            help="Do not collect environment variables")
        parser.add_argument("--no-postproc", default=False, dest="no_postproc",
                            action="store_true",
                            help="Disable all post-processing")
        parser.add_argument("--note", type=str, action="store", default="",
                            help="Behaviour notes for new preset")
        parser.add_argument("-o", "--only-plugins", action="extend",
                            dest="onlyplugins", type=str,
                            help="enable these plugins only", default=[])
        parser.add_argument("--preset", action="store", type=str,
                            help="A preset identifier", default="auto")
        parser.add_argument("--plugin-timeout", default=None,
                            help="set a timeout for all plugins")
        parser.add_argument("-p", "--profile", action="extend",
                            dest="profiles", type=str, default=[],
                            help="enable plugins used by the given profiles")
        parser.add_argument("--verify", action="store_true",
                            dest="verify", default=False,
                            help="perform data verification during collection")
        parser.add_argument("-z", "--compression-type",
                            dest="compression_type",
                            default='auto',
                            help="compression technology to use [auto, "
                                 "gzip, xz] (default=auto)")
        parser.add_argument("--allow-system-changes", action="store_true",
                            dest="allow_system_changes", default=False,
                            help="Run commands even if they can change the "
                                 "system (e.g. load kernel modules)")
        parser.add_argument("--upload", action="store_true", default=False,
                            help="Upload archive to a policy-default location")
        parser.add_argument("--upload-url", default=None,
                            help="Upload the archive to the specified server")
        parser.add_argument("--upload-directory", default=None,
                            help="Specify directory to upload the archive to")
        parser.add_argument("--upload-user", default=None,
                            help="Username to authenticate to server with")
        parser.add_argument("--upload-pass", default=None,
                            help="Password to authenticate to server with")

        # Group to make add/del preset exclusive
        preset_grp = parser.add_mutually_exclusive_group()
        preset_grp.add_argument("--add-preset", type=str, action="store",
                                help="Add a new named command line preset")
        preset_grp.add_argument("--del-preset", type=str, action="store",
                                help="Delete the named command line preset")

        # Group to make tarball encryption (via GPG/password) exclusive
        encrypt_grp = parser.add_mutually_exclusive_group()
        encrypt_grp.add_argument("--encrypt-key",
                                 help="Encrypt the archive using a GPG "
                                      "key-pair")
        encrypt_grp.add_argument("--encrypt-pass",
                                 help="Encrypt the archive using a password")

    def print_header(self):
        print("\n%s\n" % _("sosreport (version %s)" % (__version__,)))

    def _get_hardware_devices(self):
        self.devices = {
            'block': self.get_block_devs(),
            'fibre': self.get_fibre_devs()
        }
        # TODO: enumerate network devices, preferably with devtype info

    def get_fibre_devs(self):
        """Enumerate a list of fibrechannel devices on this system so that
        plugins can iterate over them

        These devices are used by add_fibredev_cmd() in the Plugin class.
        """
        try:
            devs = []
            devdirs = [
                'fc_host',
                'fc_transport',
                'fc_remote_ports',
                'fc_vports'
            ]
            for devdir in devdirs:
                if os.isdir("/sys/class/%s" % devdir):
                    devs.extend(glob.glob("/sys/class/%s/*" % devdir))
            return devs
        except Exception as err:
            return []

    def get_block_devs(self):
        """Enumerate a list of block devices on this system so that plugins
        can iterate over them

        These devices are used by add_blockdev_cmd() in the Plugin class.
        """
        try:
            return os.listdir('/sys/block/')
        except Exception as err:
            self.soslog.error("Could not get block device list: %s" % err)
            return []

    def get_commons(self):
        return {
            'cmddir': self.cmddir,
            'logdir': self.logdir,
            'rptdir': self.rptdir,
            'tmpdir': self.tmpdir,
            'soslog': self.soslog,
            'policy': self.policy,
            'sysroot': self.sysroot,
            'verbosity': self.opts.verbosity,
            'cmdlineopts': self.opts,
            'devices': self.devices
        }

    def get_temp_file(self):
        return self.tempfile_util.new()

    def _make_archive_paths(self):
        self.archive.makedirs(self.cmddir, 0o755)
        self.archive.makedirs(self.logdir, 0o755)
        self.archive.makedirs(self.rptdir, 0o755)

    def _set_directories(self):
        self.cmddir = 'sos_commands'
        self.logdir = 'sos_logs'
        self.rptdir = 'sos_reports'

    def _set_debug(self):
        if self.opts.debug:
            sys.excepthook = self._exception
            self.raise_plugins = True
        else:
            self.raise_plugins = False

    @staticmethod
    def _exception(etype, eval_, etrace):
        """ Wrap exception in debugger if not in tty """
        if hasattr(sys, 'ps1') or not sys.stderr.isatty():
            # we are in interactive mode or we don't have a tty-like
            # device, so we call the default hook
            sys.__excepthook__(etype, eval_, etrace)
        else:
            # we are NOT in interactive mode, print the exception...
            traceback.print_exception(etype, eval_, etrace, limit=2,
                                      file=sys.stdout)
            print()
            # ...then start the debugger in post-mortem mode.
            pdb.pm()

    def handle_exception(self, plugname=None, func=None):
        if self.raise_plugins or self.exit_process:
            # retrieve exception info for the current thread and stack.
            (etype, val, tb) = sys.exc_info()
            # we are NOT in interactive mode, print the exception...
            traceback.print_exception(etype, val, tb, file=sys.stdout)
            print()
            # ...then start the debugger in post-mortem mode.
            pdb.post_mortem(tb)
        if plugname and func:
            self._log_plugin_exception(plugname, func)

    def _add_sos_logs(self):
        # Make sure the log files are added before we remove the log
        # handlers. This prevents "No handlers could be found.." messages
        # from leaking to the console when running in --quiet mode when
        # Archive classes attempt to acess the log API.
        if getattr(self, "sos_log_file", None):
            self.archive.add_file(self.sos_log_file,
                                  dest=os.path.join('sos_logs', 'sos.log'))
        if getattr(self, "sos_ui_log_file", None):
            self.archive.add_file(self.sos_ui_log_file,
                                  dest=os.path.join('sos_logs', 'ui.log'))

    def _is_in_profile(self, plugin_class):
        onlyplugins = self.opts.onlyplugins
        if not len(self.opts.profiles):
            return True
        if not hasattr(plugin_class, "profiles"):
            return False
        if onlyplugins and not self._is_not_specified(plugin_class.name()):
            return True
        return any([p in self.opts.profiles for p in plugin_class.profiles])

    def _is_skipped(self, plugin_name):
        return (plugin_name in self.opts.noplugins)

    def _is_inactive(self, plugin_name, pluginClass):
        return (not pluginClass(self.get_commons()).check_enabled() and
                plugin_name not in self.opts.enableplugins and
                plugin_name not in self.opts.onlyplugins)

    def _is_not_default(self, plugin_name, pluginClass):
        return (not pluginClass(self.get_commons()).default_enabled() and
                plugin_name not in self.opts.enableplugins and
                plugin_name not in self.opts.onlyplugins)

    def _is_not_specified(self, plugin_name):
        return (self.opts.onlyplugins and
                plugin_name not in self.opts.onlyplugins)

    def _skip(self, plugin_class, reason="unknown"):
        self.skipped_plugins.append((
            plugin_class.name(),
            plugin_class(self.get_commons()),
            reason
        ))

    def _load(self, plugin_class):
        self.loaded_plugins.append((
            plugin_class.name(),
            plugin_class(self.get_commons())
        ))

    def load_plugins(self):
        import_plugin = sos.report.plugins.import_plugin
        helper = ImporterHelper(sos.report.plugins)
        plugins = helper.get_modules()
        self.plugin_names = []
        self.profiles = set()
        using_profiles = len(self.opts.profiles)
        policy_classes = self.policy.valid_subclasses
        extra_classes = []

        if self.opts.experimental:
            extra_classes.append(sos.report.plugins.ExperimentalPlugin)
        valid_plugin_classes = tuple(policy_classes + extra_classes)
        validate_plugin = self.policy.validate_plugin
        remaining_profiles = list(self.opts.profiles)

        # validate and load plugins
        for plug in plugins:
            plugbase, ext = os.path.splitext(plug)
            try:
                plugin_classes = import_plugin(plugbase, valid_plugin_classes)
                if not len(plugin_classes):
                    # no valid plugin classes for this policy
                    continue

                plugin_class = self.policy.match_plugin(plugin_classes)

                if not validate_plugin(plugin_class,
                                       experimental=self.opts.experimental):
                    self.soslog.warning(
                        _("plugin %s does not validate, skipping") % plug)
                    if self.opts.verbosity > 0:
                        self._skip(plugin_class, _("does not validate"))
                        continue

                if plugin_class.requires_root and not self._is_root:
                    self.soslog.info(_("plugin %s requires root permissions"
                                       "to execute, skipping") % plug)
                    self._skip(plugin_class, _("requires root"))
                    continue

                # plug-in is valid, let's decide whether run it or not
                self.plugin_names.append(plugbase)

                in_profile = self._is_in_profile(plugin_class)
                if not in_profile:
                    self._skip(plugin_class, _("excluded"))
                    continue

                if self._is_skipped(plugbase):
                    self._skip(plugin_class, _("skipped"))
                    continue

                if self._is_inactive(plugbase, plugin_class):
                    self._skip(plugin_class, _("inactive"))
                    continue

                if self._is_not_default(plugbase, plugin_class):
                    self._skip(plugin_class, _("optional"))
                    continue

                # only add the plugin's profiles once we know it is usable
                if hasattr(plugin_class, "profiles"):
                    self.profiles.update(plugin_class.profiles)

                # true when the null (empty) profile is active
                default_profile = not using_profiles and in_profile
                if self._is_not_specified(plugbase) and default_profile:
                    self._skip(plugin_class, _("not specified"))
                    continue

                for i in plugin_class.profiles:
                    if i in remaining_profiles:
                        remaining_profiles.remove(i)
                self._load(plugin_class)
            except Exception as e:
                self.soslog.warning(_("plugin %s does not install, "
                                      "skipping: %s") % (plug, e))
                self.handle_exception()
        if len(remaining_profiles) > 0:
            self.soslog.error(_("Unknown or inactive profile(s) provided:"
                                " %s") % ", ".join(remaining_profiles))
            self.list_profiles()
            self._exit(1)

    def _set_all_options(self):
        if self.opts.alloptions:
            for plugname, plug in self.loaded_plugins:
                for name, parms in zip(plug.opt_names, plug.opt_parms):
                    if type(parms["enabled"]) == bool:
                        parms["enabled"] = True

    def _set_tunables(self):
        if self.opts.plugopts:
            opts = {}
            for opt in self.opts.plugopts:
                # split up "general.syslogsize=5"
                try:
                    opt, val = opt.split("=")
                except ValueError:
                    val = True
                else:
                    if val.lower() in ["off", "disable", "disabled", "false"]:
                        val = False
                    else:
                        # try to convert string "val" to int()
                        try:
                            val = int(val)
                        except ValueError:
                            pass

                # split up "general.syslogsize"
                try:
                    plug, opt = opt.split(".")
                except ValueError:
                    plug = opt
                    opt = True

                try:
                    opts[plug]
                except KeyError:
                    opts[plug] = []
                opts[plug].append((opt, val))

            for plugname, plug in self.loaded_plugins:
                if plugname in opts:
                    for opt, val in opts[plugname]:
                        if not plug.set_option(opt, val):
                            self.soslog.error('no such option "%s" for plugin '
                                              '(%s)' % (opt, plugname))
                            self._exit(1)
                    del opts[plugname]
            for plugname in opts.keys():
                self.soslog.error('WARNING: unable to set option for disabled '
                                  'or non-existing plugin (%s)' % (plugname))
            # in case we printed warnings above, visually intend them from
            # subsequent header text
            if opts.keys():
                self.soslog.error('')

    def _check_for_unknown_plugins(self):
        import itertools
        for plugin in itertools.chain(self.opts.onlyplugins,
                                      self.opts.noplugins,
                                      self.opts.enableplugins):
            plugin_name = plugin.split(".")[0]
            if plugin_name not in self.plugin_names:
                self.soslog.fatal('a non-existing plugin (%s) was specified '
                                  'in the command line' % (plugin_name))
                self._exit(1)

    def _set_plugin_options(self):
        for plugin_name, plugin in self.loaded_plugins:
            names, parms = plugin.get_all_options()
            for optname, optparm in zip(names, parms):
                self.all_options.append((plugin, plugin_name, optname,
                                         optparm))

    def _report_profiles_and_plugins(self):
        self.ui_log.info("")
        if len(self.loaded_plugins):
            self.ui_log.info(" %d profiles, %d plugins"
                             % (len(self.profiles), len(self.loaded_plugins)))
        else:
            # no valid plugins for this profile
            self.ui_log.info(" %d profiles" % len(self.profiles))
        self.ui_log.info("")

    def list_plugins(self):
        if not self.loaded_plugins and not self.skipped_plugins:
            self.soslog.fatal(_("no valid plugins found"))
            return

        if self.loaded_plugins:
            self.ui_log.info(_("The following plugins are currently enabled:"))
            self.ui_log.info("")
            for (plugname, plug) in self.loaded_plugins:
                self.ui_log.info(" %-20s %s" % (plugname,
                                                plug.get_description()))
        else:
            self.ui_log.info(_("No plugin enabled."))
        self.ui_log.info("")

        if self.skipped_plugins:
            self.ui_log.info(_("The following plugins are currently "
                               "disabled:"))
            self.ui_log.info("")
            for (plugname, plugclass, reason) in self.skipped_plugins:
                self.ui_log.info(" %-20s %-14s %s" % (
                    plugname,
                    reason,
                    plugclass.get_description()))
        self.ui_log.info("")

        if self.all_options:
            self.ui_log.info(_("The following options are available for ALL "
                               "plugins:"))
            for opt in self.all_options[0][0]._default_plug_opts:
                self.ui_log.info(" %-25s %-15s %s" % (opt[0], opt[3], opt[1]))
            self.ui_log.info("")

            self.ui_log.info(_("The following plugin options are available:"))
            for (plug, plugname, optname, optparm) in self.all_options:
                if optname in ('timeout', 'postproc'):
                    continue
                # format option value based on its type (int or bool)
                if type(optparm["enabled"]) == bool:
                    if optparm["enabled"] is True:
                        tmpopt = "on"
                    else:
                        tmpopt = "off"
                else:
                    tmpopt = optparm["enabled"]

                self.ui_log.info(" %-25s %-15s %s" % (
                    plugname + "." + optname, tmpopt, optparm["desc"]))
        else:
            self.ui_log.info(_("No plugin options available."))

        self.ui_log.info("")
        profiles = list(self.profiles)
        profiles.sort()
        lines = _format_list("Profiles: ", profiles, indent=True)
        for line in lines:
            self.ui_log.info(" %s" % line)
        self._report_profiles_and_plugins()

    def list_profiles(self):
        if not self.profiles:
            self.soslog.fatal(_("no valid profiles found"))
            return
        self.ui_log.info(_("The following profiles are available:"))
        self.ui_log.info("")

        def _has_prof(c):
            return hasattr(c, "profiles")

        profiles = list(self.profiles)
        profiles.sort()
        for profile in profiles:
            plugins = []
            for name, plugin in self.loaded_plugins:
                if _has_prof(plugin) and profile in plugin.profiles:
                    plugins.append(name)
            lines = _format_list("%-15s " % profile, plugins, indent=True)
            for line in lines:
                self.ui_log.info(" %s" % line)
        self._report_profiles_and_plugins()

    def list_presets(self):
        if not self.policy.presets:
            self.soslog.fatal(_("no valid presets found"))
            return
        self.ui_log.info(_("The following presets are available:"))
        self.ui_log.info("")

        for preset in self.policy.presets.keys():
            if not preset:
                continue
            preset = self.policy.find_preset(preset)
            self.ui_log.info("%14s %s" % ("name:", preset.name))
            self.ui_log.info("%14s %s" % ("description:", preset.desc))
            if preset.note:
                self.ui_log.info("%14s %s" % ("note:", preset.note))

            if self.opts.verbosity > 0:
                args = preset.opts.to_args()
                options_str = "%14s " % "options:"
                lines = _format_list(options_str, args, indent=True, sep=' ')
                for line in lines:
                    self.ui_log.info(line)
            self.ui_log.info("")

    def add_preset(self, name, desc="", note=""):
        """Add a new command line preset for the current options with the
            specified name.

            :param name: the name of the new preset
            :returns: True on success or False otherwise
        """
        policy = self.policy
        if policy.find_preset(name):
            self.ui_log.error("A preset named '%s' already exists" % name)
            return False

        desc = desc or self.opts.desc
        note = note or self.opts.note

        try:
            policy.add_preset(name=name, desc=desc, note=note, opts=self.opts)
        except Exception as e:
            self.ui_log.error("Could not add preset: %s" % e)
            return False

        # Filter --add-preset <name> from arguments list
        arg_index = self._args.index("--add-preset")
        args = self._args[0:arg_index] + self._args[arg_index + 2:]

        self.ui_log.info("Added preset '%s' with options %s\n" %
                         (name, " ".join(args)))
        return True

    def del_preset(self, name):
        """Delete a named command line preset.

            :param name: the name of the preset to delete
            :returns: True on success or False otherwise
        """
        policy = self.policy
        if not policy.find_preset(name):
            self.ui_log.error("Preset '%s' not found" % name)
            return False

        try:
            policy.del_preset(name=name)
        except Exception as e:
            self.ui_log.error(str(e) + "\n")
            return False

        self.ui_log.info("Deleted preset '%s'\n" % name)
        return True

    def batch(self):
        if self.opts.batch:
            self.ui_log.info(self.policy.get_msg())
        else:
            msg = self.policy.get_msg()
            msg += _("Press ENTER to continue, or CTRL-C to quit.\n")
            try:
                input(msg)
            except KeyboardInterrupt as e:
                self.ui_log.error("Exiting on user cancel")
                self._exit(130)
            except Exception as e:
                self.ui_log.info("")
                self.ui_log.error(e)
                self._exit(e)

    def _log_plugin_exception(self, plugin, method):
        trace = traceback.format_exc()
        msg = "caught exception in plugin method"
        plugin_err_log = "%s-plugin-errors.txt" % plugin
        logpath = os.path.join(self.logdir, plugin_err_log)
        self.soslog.error('%s "%s.%s()"' % (msg, plugin, method))
        self.soslog.error('writing traceback to %s' % logpath)
        self.archive.add_string("%s\n" % trace, logpath, mode='a')

    def prework(self):
        self.policy.pre_work()
        try:
            self.ui_log.info(_(" Setting up archive ..."))
            compression_methods = ('auto', 'bzip2', 'gzip', 'xz')
            method = self.opts.compression_type
            if method not in compression_methods:
                compression_list = ', '.join(compression_methods)
                self.ui_log.error("")
                self.ui_log.error("Invalid compression specified: " + method)
                self.ui_log.error("Valid types are: " + compression_list)
                self.ui_log.error("")
                self._exit(1)
            self.setup_archive()
            self._make_archive_paths()
            return
        except (OSError, IOError) as e:
            # we must not use the logging subsystem here as it is potentially
            # in an inconsistent or unreliable state (e.g. an EROFS for the
            # file system containing our temporary log files).
            if e.errno in fatal_fs_errors:
                print("")
                print(" %s while setting up archive" % e.strerror)
                print("")
            else:
                print("Error setting up archive: %s" % e)
                raise
        except Exception as e:
            self.ui_log.error("")
            self.ui_log.error(" Unexpected exception setting up archive:")
            traceback.print_exc()
            self.ui_log.error(e)
        self._exit(1)

    def setup(self):
        # Log command line options
        msg = "[%s:%s] executing 'sos %s'"
        self.soslog.info(msg % (__name__, "setup", " ".join(self.cmdline)))

        # Log active preset defaults
        preset_args = self.preset.opts.to_args()
        msg = ("[%s:%s] using '%s' preset defaults (%s)" %
               (__name__, "setup", self.preset.name, " ".join(preset_args)))
        self.soslog.info(msg)

        # Log effective options after applying preset defaults
        self.soslog.info("[%s:%s] effective options now: %s" %
                         (__name__, "setup", " ".join(self.opts.to_args())))

        self.ui_log.info(_(" Setting up plugins ..."))
        for plugname, plug in self.loaded_plugins:
            try:
                plug.archive = self.archive
                plug.add_default_collections()
                plug.setup()
                self.env_vars.update(plug._env_vars)
                if self.opts.verify:
                    plug.setup_verify()
            except KeyboardInterrupt:
                raise
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(" %s while setting up plugins"
                                      % e.strerror)
                    self.ui_log.error("")
                    self._exit(1)
                self.handle_exception(plugname, "setup")
            except Exception:
                self.handle_exception(plugname, "setup")

    def version(self):
        """Fetch version information from all plugins and store in the report
        version file"""

        versions = []
        versions.append("sosreport: %s" % __version__)

        for plugname, plug in self.loaded_plugins:
            versions.append("%s: %s" % (plugname, plug.version))

        self.archive.add_string(content="\n".join(versions),
                                dest='version.txt')

    def collect(self):
        self.ui_log.info(_(" Running plugins. Please wait ..."))
        self.ui_log.info("")

        plugruncount = 0
        self.pluglist = []
        self.running_plugs = []
        for i in self.loaded_plugins:
            plugruncount += 1
            self.pluglist.append((plugruncount, i[0]))
        try:
            self.plugpool = ThreadPoolExecutor(self.opts.threads)
            # Pass the plugpool its own private copy of self.pluglist
            results = self.plugpool.map(self._collect_plugin,
                                        list(self.pluglist))
            self.plugpool.shutdown(wait=True)
            for res in results:
                if not res:
                    self.soslog.debug("Unexpected plugin task result: %s" %
                                      res)
            self.ui_log.info("")
        except KeyboardInterrupt:
            # We may not be at a newline when the user issues Ctrl-C
            self.ui_log.error("\nExiting on user cancel\n")
            os._exit(1)

    def _collect_plugin(self, plugin):
        """Wraps the collect_plugin() method so we can apply a timeout
        against the plugin as a whole"""
        with ThreadPoolExecutor(1) as pool:
            try:
                t = pool.submit(self.collect_plugin, plugin)
                # Re-type int 0 to NoneType, as otherwise result() will treat
                # it as a literal 0-second timeout
                timeout = self.loaded_plugins[plugin[0]-1][1].timeout or None
                t.result(timeout=timeout)
            except TimeoutError:
                self.ui_log.error("\n Plugin %s timed out\n" % plugin[1])
                self.running_plugs.remove(plugin[1])
                self.loaded_plugins[plugin[0]-1][1]._timeout_hit = True
                pool._threads.clear()
        return True

    def collect_plugin(self, plugin):
        try:
            count, plugname = plugin
            plug = self.loaded_plugins[count-1][1]
            self.running_plugs.append(plugname)
        except Exception:
            return False
        numplugs = len(self.loaded_plugins)
        status_line = "  Starting %-5s %-15s %s" % (
            "%d/%d" % (count, numplugs),
            plugname,
            "[Running: %s]" % ' '.join(p for p in self.running_plugs)
        )
        self.ui_progress(status_line)
        try:
            plug.collect()
            # certain exceptions can cause either of these lists to no
            # longer contain the plugin, which will result in sos hanging
            # so we can't blindly call remove() on these two.
            try:
                self.pluglist.remove(plugin)
            except ValueError:
                pass
            try:
                self.running_plugs.remove(plugname)
            except ValueError:
                pass
            status = ''
            if (len(self.pluglist) <= int(self.opts.threads) and
                    self.running_plugs):
                status = "  Finishing plugins %-12s %s" % (
                    " ",
                    "[Running: %s]" % (' '.join(p for p in self.running_plugs))
                )
            if not self.running_plugs and not self.pluglist:
                status = "\n  Finished running plugins"
            if status:
                self.ui_progress(status)
        except SoSTimeoutError:
            # we already log and handle the plugin timeout in the nested thread
            # pool this is running in, so don't do anything here.
            pass
        except (OSError, IOError) as e:
            if e.errno in fatal_fs_errors:
                self.ui_log.error("\n %s while collecting plugin data\n"
                                  % e.strerror)
                self._exit(1)
            self.handle_exception(plugname, "collect")
        except Exception:
            self.handle_exception(plugname, "collect")

    def ui_progress(self, status_line):
        if self.opts.verbosity == 0 and not self.opts.batch:
            status_line = "\r%s" % status_line.ljust(90)
        else:
            status_line = "%s\n" % status_line
        if not self.opts.quiet:
            sys.stdout.write(status_line)
            sys.stdout.flush()

    def collect_env_vars(self):
        if not self.env_vars:
            return
        env = '\n'.join([
            "%s=%s" % (name, val) for (name, val) in
            [(name, '%s' % os.environ.get(name)) for name in self.env_vars if
             os.environ.get(name) is not None]
        ]) + '\n'
        self.archive.add_string(env, 'environment')

    def generate_reports(self):
        report = Report()

        # generate report content
        for plugname, plug in self.loaded_plugins:
            section = Section(name=plugname)

            for alert in plug.alerts:
                section.add(Alert(alert))

            if plug.custom_text:
                section.add(Note(plug.custom_text))

            for f in plug.copied_files:
                section.add(CopiedFile(name=f['srcpath'],
                                       href=".." + f['dstpath']))

            for cmd in plug.executed_commands:
                section.add(Command(name=cmd['cmd'], return_code=0,
                                    href=os.path.join(
                                        "..",
                                        self.get_commons()['cmddir'],
                                        cmd['file']
                                    )))

            for content, f in plug.copy_strings:
                section.add(CreatedFile(name=f,
                                        href=os.path.join(
                                            "..",
                                            "sos_strings",
                                            plugname,
                                            f)))

            report.add(section)

        # print it in text, JSON and HTML formats
        formatlist = (
            (PlainTextReport, "sos.txt",  "text"),
            (JSONReport,      "sos.json", "JSON"),
            (HTMLReport,      "sos.html", "HTML")
        )
        for class_, filename, type_ in formatlist:
            try:
                fd = self.get_temp_file()
                output = class_(report).unicode()
                fd.write(output)
                fd.flush()
                self.archive.add_file(fd, dest=os.path.join('sos_reports',
                                                            filename))
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(" %s while writing %s report"
                                      % (e.strerror, type_))
                    self.ui_log.error("")
                    self._exit(1)

    def postproc(self):
        for plugname, plug in self.loaded_plugins:
            try:
                if plug.get_option('postproc'):
                    plug.postproc()
                else:
                    self.soslog.info("Skipping postproc for plugin %s"
                                     % plugname)
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(" %s while post-processing plugin data"
                                      % e.strerror)
                    self.ui_log.error("")
                    self._exit(1)
                self.handle_exception(plugname, "postproc")
            except Exception:
                self.handle_exception(plugname, "postproc")

    def _create_checksum(self, archive, hash_name):
        if not archive:
            return False

        try:
            hash_size = 1024**2  # Hash 1MiB of content at a time.
            archive_fp = open(archive, 'rb')
            digest = hashlib.new(hash_name)
            while True:
                hashdata = archive_fp.read(hash_size)
                if not hashdata:
                    break
                digest.update(hashdata)
            archive_fp.close()
        except Exception:
            self.handle_exception()
        return digest.hexdigest()

    def _write_checksum(self, archive, hash_name, checksum):
        # store checksum into file
        fp = open(archive + "." + hash_name, "w")
        if checksum:
            fp.write(checksum + "\n")
        fp.close()

    def final_work(self):
        # This must come before archive creation to ensure that log
        # files are closed and cleaned up at exit.
        #
        # All subsequent terminal output must use print().
        self._add_sos_logs()

        archive = None    # archive path
        directory = None  # report directory path (--build)

        # package up and compress the results
        if not self.opts.build:
            old_umask = os.umask(0o077)
            if not self.opts.quiet:
                print(_("Creating compressed archive..."))
            # compression could fail for a number of reasons
            try:
                archive = self.archive.finalize(
                    self.opts.compression_type)
            except (OSError, IOError) as e:
                print("")
                print(_(" %s while finalizing archive %s" %
                        (e.strerror, self.archive.get_archive_path())))
                print("")
                if e.errno in fatal_fs_errors:
                    self._exit(1)
            except Exception:
                if self.opts.debug:
                    raise
                else:
                    return False
            finally:
                os.umask(old_umask)
        else:
            # move the archive root out of the private tmp directory.
            directory = self.archive.get_archive_path()
            dir_name = os.path.basename(directory)
            try:
                final_dir = os.path.join(self.sys_tmp, dir_name)
                os.rename(directory, final_dir)
                directory = final_dir
            except (OSError, IOError):
                print(_("Error moving directory: %s" % directory))
                return False

        checksum = None

        if not self.opts.build:
            # if creating archive file failed, report it and
            # skip generating checksum
            if not archive:
                print("Creating archive tarball failed.")
            else:
                # compute and store the archive checksum
                hash_name = self.policy.get_preferred_hash_name()
                checksum = self._create_checksum(archive, hash_name)
                try:
                    self._write_checksum(archive, hash_name, checksum)
                except (OSError, IOError):
                    print(_("Error writing checksum for file: %s" % archive))

                # output filename is in the private tmpdir - move it to the
                # containing directory.
                final_name = os.path.join(self.sys_tmp,
                                          os.path.basename(archive))
                # Get stat on the archive
                archivestat = os.stat(archive)

                archive_hash = archive + "." + hash_name
                final_hash = final_name + "." + hash_name

                # move the archive and checksum file
                try:
                    os.rename(archive, final_name)
                    archive = final_name
                except (OSError, IOError):
                    print(_("Error moving archive file: %s" % archive))
                    return False

                # There is a race in the creation of the final checksum file:
                # since the archive has already been published and the checksum
                # file name is predictable once the archive name is known a
                # malicious user could attempt to create a symbolic link in
                # order to misdirect writes to a file of the attacker's choose.
                #
                # To mitigate this we write the checksum inside the private tmp
                # directory and use an atomic rename that is guaranteed to
                # either succeed or fail: at worst the move will fail and be
                # reported to the user. The correct checksum value is still
                # written to the terminal and nothing is written to a location
                # under the control of the user creating the link.
                try:
                    os.rename(archive_hash, final_hash)
                except (OSError, IOError):
                    print(_("Error moving checksum file: %s" % archive_hash))

        if not self.opts.build:
            self.policy.display_results(archive, directory, checksum,
                                        archivestat)
        else:
            self.policy.display_results(archive, directory, checksum)

        if self.opts.upload or self.opts.upload_url:
            if not self.opts.build:
                try:
                    self.policy.upload_archive(archive)
                    self.ui_log.info(_("Uploaded archive successfully"))
                except Exception as err:
                    self.ui_log.error("Upload attempt failed: %s" % err)
            else:
                msg = ("Unable to upload archive when using --build as no "
                       "archive is created.")
                self.ui_log.error(msg)

        # clean up
        logging.shutdown()
        if self.tempfile_util:
            self.tempfile_util.clean()
        if self.tmpdir and os.path.isdir(self.tmpdir):
            rmtree(self.tmpdir)

        return True

    def verify_plugins(self):
        if not self.loaded_plugins:
            self.soslog.error(_("no valid plugins were enabled"))
            return False
        return True

    def execute(self):
        try:
            self.policy.set_commons(self.get_commons())
            self.load_plugins()
            self._set_all_options()
            self._set_tunables()
            self._check_for_unknown_plugins()
            self._set_plugin_options()

            if self.opts.list_plugins:
                self.list_plugins()
                raise SystemExit
            if self.opts.list_profiles:
                self.list_profiles()
                raise SystemExit
            if self.opts.list_presets:
                self.list_presets()
                raise SystemExit
            if self.opts.add_preset:
                return self.add_preset(self.opts.add_preset)
            if self.opts.del_preset:
                return self.del_preset(self.opts.del_preset)
            # verify that at least one plug-in is enabled
            if not self.verify_plugins():
                return False

            self.batch()
            self.prework()
            self.setup()
            self.collect()
            if not self.opts.no_env_vars:
                self.collect_env_vars()
            if not self.opts.noreport:
                self.generate_reports()
            if not self.opts.no_postproc:
                self.postproc()
            else:
                self.ui_log.info("Skipping postprocessing of collected data")
            self.version()
            return self.final_work()

        except (OSError):
            if self.opts.debug:
                raise
            self.cleanup()
        except (KeyboardInterrupt):
            self.ui_log.error("\nExiting on user cancel")
            self.cleanup()
            self._exit(130)
        except (SystemExit) as e:
            self.cleanup()
            sys.exit(e.code)

        self._exit(1)

# vim: set et ts=4 sw=4 :
