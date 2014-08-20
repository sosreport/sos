"""
Gather information about a system and report it using plugins
supplied for application-specific information
"""
# sosreport.py
# gather information about a system and report it

# Copyright (C) 2006 Steve Conklin <sconklin@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sys
import traceback
import os
import errno
import logging
from optparse import OptionParser, Option
from sos.plugins import import_plugin
from sos.utilities import ImporterHelper
from stat import ST_UID, ST_GID, ST_MODE, ST_CTIME, ST_ATIME, ST_MTIME, S_IMODE
from time import strftime, localtime
from collections import deque
import tempfile

from sos import _sos as _
from sos import __version__
import sos.policies
from sos.archive import TarFileArchive, ZipFileArchive
from sos.reporting import (Report, Section, Command, CopiedFile, CreatedFile,
                           Alert, Note, PlainTextReport)

# PYCOMPAT
import six
from six.moves import zip, input
if six.PY3:
    from configparser import ConfigParser
else:
    from ConfigParser import ConfigParser
from six import print_

# file system errors that should terminate a run
fatal_fs_errors = (errno.ENOSPC, errno.EROFS)


class TempFileUtil(object):

    def __init__(self, tmp_dir):
        self.tmp_dir = tmp_dir
        self.files = []

    def new(self):
        fd, fname = tempfile.mkstemp(dir=self.tmp_dir)
        fobj = open(fname, 'w')
        self.files.append((fname, fobj))
        return fobj

    def clean(self):
        for fname, f in self.files:
            try:
                f.flush()
                f.close()
            except Exception:
                pass
            try:
                os.unlink(fname)
            except Exception:
                pass
        self.files = []


class OptionParserExtended(OptionParser):
    """ Show examples """
    def print_help(self, out=sys.stdout):
        """ Prints help content including examples """
        OptionParser.print_help(self, out)
        print_()
        print_("Some examples:")
        print_()
        print_(" enable cluster plugin only and collect dlm lockdumps:")
        print_("   # sosreport -o cluster -k cluster.lockdump")
        print_()
        print_(" disable memory and samba plugins, turn off rpm -Va "
               "collection:")
        print_("   # sosreport -n memory,samba -k rpm.rpmva=off")
        print_()


class SosOption(Option):
    """Allow to specify comma delimited list of plugins"""
    ACTIONS = Option.ACTIONS + ("extend",)
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extend",)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extend",)

    def take_action(self, action, dest, opt, value, values, parser):
        """ Performs list extension on plugins """
        if action == "extend":
            try:
                lvalue = value.split(",")
            except:
                pass
            else:
                values.ensure_value(dest, deque()).extend(lvalue)
        else:
            Option.take_action(self, action, dest, opt, value, values, parser)


class XmlReport(object):
    """ Report build class """

    def __init__(self):
        try:
            import libxml2
        except ImportError:
            self.enabled = False
            return
        else:
            self.enabled = False
            return
        self.doc = libxml2.newDoc("1.0")
        self.root = self.doc.newChild(None, "sos", None)
        self.commands = self.root.newChild(None, "commands", None)
        self.files = self.root.newChild(None, "files", None)

    def add_command(self, cmdline, exitcode, stdout=None, stderr=None,
                    f_stdout=None, f_stderr=None, runtime=None):
        """ Appends command run into report """
        if not self.enabled:
            return

        cmd = self.commands.newChild(None, "cmd", None)

        cmd.setNsProp(None, "cmdline", cmdline)

        cmdchild = cmd.newChild(None, "exitcode", str(exitcode))

        if runtime:
            cmd.newChild(None, "runtime", str(runtime))

        if stdout or f_stdout:
            cmdchild = cmd.newChild(None, "stdout", stdout)
            if f_stdout:
                cmdchild.setNsProp(None, "file", f_stdout)

        if stderr or f_stderr:
            cmdchild = cmd.newChild(None, "stderr", stderr)
            if f_stderr:
                cmdchild.setNsProp(None, "file", f_stderr)

    def add_file(self, fname, stats):
        """ Appends file(s) added to report """
        if not self.enabled:
            return

        cfile = self.files.newChild(None, "file", None)

        cfile.setNsProp(None, "fname", fname)

        cchild = cfile.newChild(None, "uid", str(stats[ST_UID]))
        cchild = cfile.newChild(None, "gid", str(stats[ST_GID]))
        cfile.newChild(None, "mode", str(oct(S_IMODE(stats[ST_MODE]))))
        cchild = cfile.newChild(None, "ctime",
                                strftime('%a %b %d %H:%M:%S %Y',
                                         localtime(stats[ST_CTIME])))
        cchild.setNsProp(None, "tstamp", str(stats[ST_CTIME]))
        cchild = cfile.newChild(None, "atime",
                                strftime('%a %b %d %H:%M:%S %Y',
                                         localtime(stats[ST_ATIME])))
        cchild.setNsProp(None, "tstamp", str(stats[ST_ATIME]))
        cchild = cfile.newChild(None, "mtime",
                                strftime('%a %b %d %H:%M:%S %Y',
                                         localtime(stats[ST_MTIME])))
        cchild.setNsProp(None, "tstamp", str(stats[ST_MTIME]))

    def serialize(self):
        """ Serializes xml """
        if not self.enabled:
            return

        self.ui_log.info(self.doc.serialize(None,  1))

    def serialize_to_file(self, fname):
        """ Serializes to file """
        if not self.enabled:
            return

        outf = tempfile.NamedTemporaryFile()
        outf.write(self.doc.serialize(None, 1))
        outf.flush()
        self.archive.add_file(outf.name, dest=fname)
        outf.close()


class SoSOptions(object):
    _list_plugins = False
    _noplugins = []
    _enableplugins = []
    _onlyplugins = []
    _plugopts = []
    _usealloptions = False
    _all_logs = False
    _log_size = 10
    _batch = False
    _build = False
    _verbosity = 0
    _verify = False
    _quiet = False
    _debug = False
    _ticket_number = ""
    _customer_name = ""
    _config_file = ""
    _tmp_dir = ""
    _report = True
    _compression_type = 'auto'

    _options = None

    def __init__(self, args=None):
        if args:
            self._options = self._parse_args(args)
        else:
            self._options = None

    def _check_options_initialized(self):
        if self._options is not None:
            raise ValueError("SoSOptions object already initialized "
                             + "from command line")

    @property
    def list_plugins(self):
        if self._options is not None:
            return self._options.list_plugins
        return self._list_plugins

    @list_plugins.setter
    def list_plugins(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.list_plugins expects a boolean")
        self._list_plugins = value

    @property
    def noplugins(self):
        if self._options is not None:
            return self._options.noplugins
        return self._noplugins

    @noplugins.setter
    def noplugins(self, value):
        self._check_options_initialized()
        self._noplugins = value

    @property
    def enableplugins(self):
        if self._options is not None:
            return self._options.enableplugins
        return self._enableplugins

    @enableplugins.setter
    def enableplugins(self, value):
        self._check_options_initialized()
        self._enableplugins = value

    @property
    def onlyplugins(self):
        if self._options is not None:
            return self._options.onlyplugins
        return self._onlyplugins

    @onlyplugins.setter
    def onlyplugins(self, value):
        self._check_options_initialized()
        self._onlyplugins = value

    @property
    def plugopts(self):
        if self._options is not None:
            return self._options.plugopts
        return self._plugopts

    @plugopts.setter
    def plugopts(self, value):
        # If we check for anything it should be itterability.
        # if not isinstance(value, list):
        #    raise TypeError("SoSOptions.plugopts expects a list")
        self._plugopts = value

    @property
    def usealloptions(self):
        if self._options is not None:
            return self._options.usealloptions
        return self._usealloptions

    @usealloptions.setter
    def usealloptions(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.usealloptions expects a boolean")
        self._usealloptions = value

    @property
    def all_logs(self):
        if self._options is not None:
            return self._options.all_logs
        return self._all_logs

    @all_logs.setter
    def all_logs(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.all_logs expects a boolean")
        self._all_logs = value

    @property
    def log_size(self):
        if self._options is not None:
            return self._options.log_size
        return self._log_size

    @log_size.setter
    def log_size(self, value):
        self._check_options_initialized()
        if value < 0:
            raise ValueError("SoSOptions.log_size expects a value greater "
                             "than zero")
        self._log_size = value

    @property
    def batch(self):
        if self._options is not None:
            return self._options.batch
        return self._batch

    @batch.setter
    def batch(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.batch expects a boolean")
        self._batch = value

    @property
    def build(self):
        if self._options is not None:
            return self._options.build
        return self._build

    @build.setter
    def build(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.build expects a boolean")
        self._build = value

    @property
    def verbosity(self):
        if self._options is not None:
            return self._options.verbosity
        return self._verbosity

    @verbosity.setter
    def verbosity(self, value):
        self._check_options_initialized()
        if value < 0 or value > 3:
            raise ValueError("SoSOptions.verbosity expects a value [0..3]")
        self._verbosity = value

    @property
    def verify(self):
        if self._options is not None:
            return self._options.verify
        return self._verify

    @verify.setter
    def verify(self, value):
        self._check_options_initialized()
        if value < 0 or value > 3:
            raise ValueError("SoSOptions.verify expects a value [0..3]")
        self._verify = value

    @property
    def quiet(self):
        if self._options is not None:
            return self._options.quiet
        return self._quiet

    @quiet.setter
    def quiet(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.quiet expects a boolean")
        self._quiet = value

    @property
    def debug(self):
        if self._options is not None:
            return self._options.debug
        return self._debug

    @debug.setter
    def debug(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.debug expects a boolean")
        self._debug = value

    @property
    def ticket_number(self):
        if self._options is not None:
            return self._options.ticket_number
        return self._ticket_number

    @ticket_number.setter
    def ticket_number(self, value):
        self._check_options_initialized()
        self._ticket_number = value

    @property
    def customer_name(self):
        if self._options is not None:
            return self._options.customer_name
        return self._customer_name

    @customer_name.setter
    def customer_name(self, value):
        self._check_options_initialized()
        self._customer_name = value

    @property
    def config_file(self):
        if self._options is not None:
            return self._options.config_file
        return self._config_file

    @config_file.setter
    def config_file(self, value):
        self._check_options_initialized()
        self._config_file = value

    @property
    def tmp_dir(self):
        if self._options is not None:
            return self._options.tmp_dir
        return self._tmp_dir

    @tmp_dir.setter
    def tmp_dir(self, value):
        self._check_options_initialized()
        self._tmp_dir = value

    @property
    def report(self):
        if self._options is not None:
            return self._options.report
        return self._report

    @report.setter
    def report(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.report expects a boolean")
        self._report = value

    @property
    def compression_type(self):
        if self._options is not None:
            return self._options.compression_type
        return self._compression_type

    @compression_type.setter
    def compression_type(self, value):
        self._check_options_initialized()
        self._compression_type = value

    def _parse_args(self, args):
        """ Parse command line options and arguments"""

        self.parser = parser = OptionParserExtended(option_class=SosOption)
        parser.add_option("-l", "--list-plugins", action="store_true",
                          dest="list_plugins", default=False,
                          help="list plugins and available plugin options")
        parser.add_option("-n", "--skip-plugins", action="extend",
                          dest="noplugins", type="string",
                          help="disable these plugins", default=deque())
        parser.add_option("-e", "--enable-plugins", action="extend",
                          dest="enableplugins", type="string",
                          help="enable these plugins", default=deque())
        parser.add_option("-o", "--only-plugins", action="extend",
                          dest="onlyplugins", type="string",
                          help="enable these plugins only", default=deque())
        parser.add_option("-k", "--plugin-option", action="extend",
                          dest="plugopts", type="string",
                          help="plugin options in plugname.option=value "
                               "format (see -l)",
                          default=deque())
        parser.add_option("--log-size", action="store",
                          dest="log_size", default=10, type="int",
                          help="set a limit on the size of collected logs")
        parser.add_option("-a", "--alloptions", action="store_true",
                          dest="usealloptions", default=False,
                          help="enable all options for loaded plugins")
        parser.add_option("--all-logs", action="store_true",
                          dest="all_logs", default=False,
                          help="collect all available logs regardless of size")
        parser.add_option("--batch", action="store_true",
                          dest="batch", default=False,
                          help="batch mode - do not prompt interactively")
        parser.add_option("--build", action="store_true",
                          dest="build", default=False,
                          help="preserve the temporary directory and do not "
                               "package results")
        parser.add_option("-v", "--verbose", action="count",
                          dest="verbosity",
                          help="increase verbosity")
        parser.add_option("", "--verify", action="store_true",
                          dest="verify", default=False,
                          help="perform data verification during collection")
        parser.add_option("", "--quiet", action="store_true",
                          dest="quiet", default=False,
                          help="only print fatal errors")
        parser.add_option("--debug", action="count",
                          dest="debug",
                          help="enable interactive debugging using the python "
                               "debugger")
        parser.add_option("--ticket-number", action="store",
                          dest="ticket_number",
                          help="specify ticket number")
        parser.add_option("--name", action="store",
                          dest="customer_name",
                          help="specify report name")
        parser.add_option("--config-file", action="store",
                          dest="config_file",
                          help="specify alternate configuration file")
        parser.add_option("--tmp-dir", action="store",
                          dest="tmp_dir",
                          help="specify alternate temporary directory",
                          default=None)
        parser.add_option("--no-report", action="store_true",
                          dest="report",
                          help="Disable HTML/XML reporting", default=False)
        parser.add_option("-z", "--compression-type", dest="compression_type",
                          help="compression technology to use [auto, zip, "
                               "gzip, bzip2, xz] (default=auto)",
                          default="auto")

        return parser.parse_args(args)[0]


class SoSReport(object):
    """The main sosreport class"""

    def __init__(self, args):
        self.loaded_plugins = deque()
        self.skipped_plugins = deque()
        self.all_options = deque()
        self.xml_report = XmlReport()
        self.global_plugin_options = {}
        self.archive = None
        self.tempfile_util = None

        try:
            import signal
            signal.signal(signal.SIGTERM, self.get_exit_handler())
        except Exception:
            pass  # not available in java, but we don't care

        self.opts = SoSOptions(args)
        self._set_debug()
        self._read_config()

        try:
            self.policy = sos.policies.load()
        except KeyboardInterrupt:
            self._exit(0)

        self._is_root = self.policy.is_root()

        self.tmpdir = os.path.abspath(
            self.policy.get_tmp_dir(self.opts.tmp_dir))
        if not os.path.isdir(self.tmpdir) \
                or not os.access(self.tmpdir, os.W_OK):
            # write directly to stderr as logging is not initialised yet
            sys.stderr.write("temporary directory %s " % self.tmpdir
                             + "does not exist or is not writable\n")
            self._exit(1)
        self.tempfile_util = TempFileUtil(self.tmpdir)
        self._set_directories()

    def print_header(self):
        self.ui_log.info("\n%s\n" % _("sosreport (version %s)" %
                         (__version__,)))

    def get_commons(self):
        return {
            'cmddir': self.cmddir,
            'logdir': self.logdir,
            'rptdir': self.rptdir,
            'tmpdir': self.tmpdir,
            'soslog': self.soslog,
            'policy': self.policy,
            'verbosity': self.opts.verbosity,
            'xmlreport': self.xml_report,
            'cmdlineopts': self.opts,
            'config': self.config,
            'global_plugin_options': self.global_plugin_options,
            }

    def get_temp_file(self):
        return self.tempfile_util.new()

    def _set_archive(self):
        archive_name = os.path.join(self.tmpdir,
                                    self.policy.get_archive_name())
        if self.opts.compression_type == 'auto':
            auto_archive = self.policy.get_preferred_archive()
            self.archive = auto_archive(archive_name, self.tmpdir)
        elif self.opts.compression_type == 'zip':
            self.archive = ZipFileArchive(archive_name, self.tmpdir)
        else:
            self.archive = TarFileArchive(archive_name, self.tmpdir)
        self.archive.set_debug(True if self.opts.debug else False)

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
            import pdb
            # we are NOT in interactive mode, print the exception...
            traceback.print_exception(etype, eval_, etrace, limit=2,
                                      file=sys.stdout)
            print_()
            # ...then start the debugger in post-mortem mode.
            pdb.pm()

    def _exit(self, error=0):
        raise SystemExit()
#        sys.exit(error)

    def get_exit_handler(self):
        def exit_handler(signum, frame):
            self._exit()
        return exit_handler

    def _read_config(self):
        self.config = ConfigParser()
        if self.opts.config_file:
            config_file = self.opts.config_file
        else:
            config_file = '/etc/sos.conf'
        try:
            self.config.readfp(open(config_file))
        except IOError:
            pass

    def _setup_logging(self):
        # main soslog
        self.soslog = logging.getLogger('sos')
        self.soslog.setLevel(logging.DEBUG)
        self.sos_log_file = self.get_temp_file()
        self.sos_log_file.close()
        flog = logging.FileHandler(self.sos_log_file.name)
        flog.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'))
        flog.setLevel(logging.INFO)
        self.soslog.addHandler(flog)

        if not self.opts.quiet:
            console = logging.StreamHandler(sys.stderr)
            console.setFormatter(logging.Formatter('%(message)s'))
            if self.opts.verbosity and self.opts.verbosity > 1:
                console.setLevel(logging.DEBUG)
                flog.setLevel(logging.DEBUG)
            elif self.opts.verbosity and self.opts.verbosity > 0:
                console.setLevel(logging.INFO)
                flog.setLevel(logging.DEBUG)
            else:
                console.setLevel(logging.WARNING)
            self.soslog.addHandler(console)

        # ui log
        self.ui_log = logging.getLogger('sos_ui')
        self.ui_log.setLevel(logging.INFO)
        self.sos_ui_log_file = self.get_temp_file()
        self.sos_ui_log_file.close()
        ui_fhandler = logging.FileHandler(self.sos_ui_log_file.name)
        ui_fhandler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'))

        self.ui_log.addHandler(ui_fhandler)

        if not self.opts.quiet:
            ui_console = logging.StreamHandler(sys.stdout)
            ui_console.setFormatter(logging.Formatter('%(message)s'))
            ui_console.setLevel(logging.INFO)
            self.ui_log.addHandler(ui_console)

    def _finish_logging(self):
        logging.shutdown()

        # the logging module seems to persist in the jython/jboss/eap world
        # so the handlers need to be removed
        for logger in [logging.getLogger(x) for x in ('sos', 'sos_ui')]:
            for h in logger.handlers:
                logger.removeHandler(h)

        if getattr(self, "sos_log_file", None):
            self.archive.add_file(self.sos_log_file.name,
                                  dest=os.path.join('sos_logs', 'sos.log'))
        if getattr(self, "sos_ui_log_file", None):
            self.archive.add_file(self.sos_ui_log_file.name,
                                  dest=os.path.join('sos_logs', 'ui.log'))

    def _get_disabled_plugins(self):
        disabled = []
        if self.config.has_option("plugins", "disable"):
            disabled = [plugin.strip() for plugin in
                        self.config.get("plugins", "disable").split(',')]
        return disabled

    def _is_skipped(self, plugin_name):
        return (plugin_name in self.opts.noplugins or
                plugin_name in self._get_disabled_plugins())

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

        import sos.plugins
        helper = ImporterHelper(sos.plugins)
        plugins = helper.get_modules()
        self.plugin_names = deque()

        # validate and load plugins
        for plug in plugins:
            plugbase, ext = os.path.splitext(plug)
            try:
                plugin_classes = import_plugin(
                    plugbase, tuple(self.policy.valid_subclasses))
                if not len(plugin_classes):
                    # no valid plugin classes for this policy
                    continue

                plugin_class = self.policy.match_plugin(plugin_classes)
                if not self.policy.validate_plugin(plugin_class):
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

                if self._is_skipped(plugbase):
                    self._skip(plugin_class, _("skipped"))
                    continue

                if self._is_inactive(plugbase, plugin_class):
                    self._skip(plugin_class, _("inactive"))
                    continue

                if self._is_not_default(plugbase, plugin_class):
                    self._skip(plugin_class, _("not default"))
                    continue

                if self._is_not_specified(plugbase):
                    self._skip(plugin_class, _("not specified"))
                    continue

                self._load(plugin_class)
            except Exception as e:
                self.soslog.warning(_("plugin %s does not install, "
                                    "skipping: %s") % (plug, e))
                if self.raise_plugins:
                    raise

    def _set_all_options(self):
        if self.opts.usealloptions:
            for plugname, plug in self.loaded_plugins:
                for name, parms in zip(plug.opt_names, plug.opt_parms):
                    if type(parms["enabled"]) == bool:
                        parms["enabled"] = True

    def _set_tunables(self):
        if self.config.has_section("tunables"):
            if not self.opts.plugopts:
                self.opts.plugopts = deque()

            for opt, val in self.config.items("tunables"):
                if not opt.split('.')[0] in self._get_disabled_plugins():
                    self.opts.plugopts.append(opt + "=" + val)
        if self.opts.plugopts:
            opts = {}
            for opt in self.opts.plugopts:
                # split up "general.syslogsize=5"
                try:
                    opt, val = opt.split("=")
                except:
                    val = True
                else:
                    if val.lower() in ["off", "disable", "disabled", "false"]:
                        val = False
                    else:
                        # try to convert string "val" to int()
                        try:
                            val = int(val)
                        except:
                            pass

                # split up "general.syslogsize"
                try:
                    plug, opt = opt.split(".")
                except:
                    plug = opt
                    opt = True

                try:
                    opts[plug]
                except KeyError:
                    opts[plug] = deque()
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
                self.soslog.error('unable to set option for disabled or '
                                  'non-existing plugin (%s)' % (plugname))

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
            self.ui_log.info(_("The following plugin options are available:"))
            self.ui_log.info("")
            for (plug, plugname, optname, optparm) in self.all_options:
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

    def batch(self):
        if self.opts.batch:
            self.ui_log.info(self.policy.get_msg())
        else:
            msg = self.policy.get_msg()
            msg += _("Press ENTER to continue, or CTRL-C to quit.\n")
            try:
                input(msg)
            except:
                self.ui_log.info("")
                self._exit()

    def _log_plugin_exception(self, plugin_name):
        self.soslog.error("%s\n%s" % (plugin_name, traceback.format_exc()))

    def prework(self):
        self.policy.pre_work()
        try:
            self.ui_log.info(_(" Setting up archive ..."))
            compression_methods = ('auto', 'zip', 'bzip2', 'gzip', 'xz')
            method = self.opts.compression_type
            if method not in compression_methods:
                compression_list = ', '.join(compression_methods)
                self.ui_log.error("")
                self.ui_log.error("Invalid compression specified: " + method)
                self.ui_log.error("Valid types are: " + compression_list)
                self.ui_log.error("")
                self._exit(1)
            self._set_archive()
            self._make_archive_paths()
            return
        except (OSError, IOError) as e:
            if e.errno in fatal_fs_errors:
                self.ui_log.error("")
                self.ui_log.error(" %s while setting up archive" % e.strerror)
                self.ui_log.error("")
            else:
                raise e
        except Exception as e:
            import traceback
            self.ui_log.error("")
            self.ui_log.error(" Unexpected exception setting up archive:")
            traceback.print_exc(e)
            self.ui_log.error(e)
        self._exit(1)

    def setup(self):
        self.ui_log.info(_(" Setting up plugins ..."))
        for plugname, plug in self.loaded_plugins:
            try:
                plug.archive = self.archive
                plug.setup()
            except KeyboardInterrupt:
                raise
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(" %s while setting up plugins"
                                      % e.strerror)
                    self.ui_log.error("")
                    self._exit(1)
            except:
                if self.raise_plugins:
                    raise
                else:
                    self._log_plugin_exception(plugname)

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
        for i in zip(self.loaded_plugins):
            plugruncount += 1
            plugname, plug = i[0]
            status_line = ("  Running %d/%d: %s...        "
                           % (plugruncount, len(self.loaded_plugins),
                              plugname))
            if self.opts.verbosity == 0:
                status_line = "\r%s" % status_line
            else:
                status_line = "%s\n" % status_line
            if not self.opts.quiet:
                sys.stdout.write(status_line)
                sys.stdout.flush()
            try:
                plug.collect()
            except KeyboardInterrupt:
                raise
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(" %s while collecting plugin data"
                                      % e.strerror)
                    self.ui_log.error("")
                    self._exit(1)
            except:
                if self.raise_plugins:
                    raise
                else:
                    self._log_plugin_exception(plugname)
        self.ui_log.info("")

    def report(self):
        for plugname, plug in self.loaded_plugins:
            for oneFile in plug.copied_files:
                try:
                    self.xml_report.add_file(oneFile["srcpath"],
                                             os.stat(oneFile["srcpath"]))
                except:
                    pass
        try:
            self.xml_report.serialize_to_file(os.path.join(self.rptdir,
                                                           "sosreport.xml"))
        except (OSError, IOError) as e:
            if e.errno in fatal_fs_errors:
                self.ui_log.error("")
                self.ui_log.error(" %s while writing report data"
                                  % e.strerror)
                self.ui_log.error("")
                self._exit(1)

    def plain_report(self):
        report = Report()

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
                section.add(Command(name=cmd['exe'], return_code=0,
                            href="../" + cmd['file']))

            for content, f in plug.copy_strings:
                section.add(CreatedFile(name=f))

            report.add(section)
        try:
            fd = self.get_temp_file()
            fd.write(str(PlainTextReport(report)))
            fd.flush()
            self.archive.add_file(fd.name, dest=os.path.join('sos_reports',
                                                             'sos.txt'))
        except (OSError, IOError) as e:
            if e.errno in fatal_fs_errors:
                self.ui_log.error("")
                self.ui_log.error(" %s while writing text report"
                                  % e.strerror)
                self.ui_log.error("")
                self._exit(1)

    def html_report(self):
        try:
            self._html_report()
        except (OSError, IOError) as e:
            if e.errno in fatal_fs_errors:
                self.ui_log.error("")
                self.ui_log.error(" %s while writing HTML report"
                                  % e.strerror)
                self.ui_log.error("")
                self._exit(1)

    def _html_report(self):
        # Generate the header for the html output file
        rfd = self.get_temp_file()
        rfd.write("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
        <head>
            <link rel="stylesheet" type="text/css" media="screen"
                  href="donot.css" />
            <meta http-equiv="Content-Type" content="text/html;
                  charset=utf-8" />
            <title>Sos System Report</title>
        </head>
        <body>
        """)

        # Make a pass to gather Alerts and a list of module names
        allAlerts = deque()
        plugNames = deque()
        for plugname, plug in self.loaded_plugins:
            for alert in plug.alerts:
                allAlerts.append('<a href="#%s">%s</a>: %s' % (plugname,
                                                               plugname,
                                                               alert))
            plugNames.append(plugname)

        # Create a table of links to the module info
        rfd.write("<hr/><h3>Loaded Plugins:</h3>")
        rfd.write("<table><tr>\n")
        rr = 0
        for i in range(len(plugNames)):
            rfd.write('<td><a href="#%s">%s</a></td>\n' % (plugNames[i],
                                                           plugNames[i]))
            rr = divmod(i, 4)[1]
            if (rr == 3):
                rfd.write('</tr>')
        if not (rr == 3):
            rfd.write('</tr>')
        rfd.write('</table>\n')

        rfd.write('<hr/><h3>Alerts:</h3>')
        rfd.write('<ul>')
        for alert in allAlerts:
            rfd.write('<li>%s</li>' % alert)
        rfd.write('</ul>')

        # Call the report method for each plugin
        for plugname, plug in self.loaded_plugins:
            try:
                html = plug.report()
            except:
                if self.raise_plugins:
                    raise
            else:
                rfd.write(html)
        rfd.write("</body></html>")
        rfd.flush()
        self.archive.add_file(rfd.name, dest=os.path.join('sos_reports',
                                                          'sos.html'))

    def postproc(self):
        for plugname, plug in self.loaded_plugins:
            try:
                plug.postproc()
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(" %s while post-processing plugin data"
                                      % e.strerror)
                    self.ui_log.error("")
                    self._exit(1)
            except:
                if self.raise_plugins:
                    raise

    def final_work(self):
        # this must come before archive creation to ensure that log
        # files are closed and cleaned up at exit.
        self._finish_logging()
        # package up the results for the support organization
        if not self.opts.build:
            print(_("Creating compressed archive..."))
            # compression could fail for a number of reasons
            try:
                final_filename = self.archive.finalize(
                    self.opts.compression_type)
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(" %s while finalizing archive"
                                      % e.strerror)
                    self.ui_log.error("")
                    self._exit(1)
            except:
                if self.opts.debug:
                    raise
                else:
                    return False
        else:
            final_filename = self.archive.get_archive_path()
        self.policy.display_results(final_filename, build=self.opts.build)
        self.tempfile_util.clean()
        return True

    def verify_plugins(self):
        if not self.loaded_plugins:
            self.soslog.error(_("no valid plugins were enabled"))
            return False
        return True

    def set_global_plugin_option(self, key, value):
        self.global_plugin_options[key] = value

    def execute(self):
        try:
            self._setup_logging()
            self.policy.set_commons(self.get_commons())
            self.print_header()
            self.load_plugins()
            self._set_all_options()
            self._set_tunables()
            self._check_for_unknown_plugins()
            self._set_plugin_options()

            if self.opts.list_plugins:
                self.list_plugins()
                return True

            # verify that at least one plug-in is enabled
            if not self.verify_plugins():
                return False

            self.batch()
            self.prework()
            self.setup()
            self.collect()
            if not self.opts.report:
                self.report()
                self.html_report()
                self.plain_report()
            self.postproc()
            self.version()

            return self.final_work()
        except (SystemExit, KeyboardInterrupt):
            if self.archive:
                self.archive.cleanup()
            if self.tempfile_util:
                self.tempfile_util.clean()
            return False


def main(args):
    """The main entry point"""
    sos = SoSReport(args)
    sos.execute()

# vim: et ts=4 sw=4
