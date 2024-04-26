# Copyright 2020 Red Hat, Inc.
# Author: Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import logging
import os
import tempfile
import sys
import time

from argparse import SUPPRESS
from datetime import datetime
from getpass import getpass
from shutil import rmtree
from pathlib import Path
from sos import __version__
from sos.archive import TarFileArchive
from sos.options import SoSOptions
from sos.utilities import TempFileUtil, shell_out


class SoSComponent():
    """Any sub-command that sos supports needs to subclass SoSComponent in
    order to be properly supported by the sos binary.

    This class contains the standardized entrypoint for subcommands, as well as
    building out supported options from both globally shared option lists, and
    options supported by that specific subcommand.

    When sos initializes, it will load an unintialized instance of each class
    found within one recursion of the module root directory that subclasses
    SoSComponent.

    If sos is able to match the user-specified subcommand to one that exists
    locally, then that SoSComponent is initialized, logging is setup, and a
    policy is loaded. From there, the component's execute() method takes over.

    Added in 4.0
    """

    desc = 'unset'

    arg_defaults = {}
    configure_logging = True
    load_policy = True
    load_probe = True
    root_required = False

    _arg_defaults = {
        "batch": False,
        "compression_type": 'auto',
        "config_file": '/etc/sos/sos.conf',
        "debug": False,
        "encrypt": False,
        "encrypt_key": None,
        "encrypt_pass": None,
        "quiet": False,
        "threads": 4,
        "tmp_dir": '',
        "sysroot": None,
        "verbosity": 0
    }

    # files in collected archive that might contain upload password
    files_with_upload_passwd = [
        "sos_logs/sos.log",
        "sos_reports/manifest.json",
        "sos_commands/process/ps_*",
        "sos_commands/selinux/ps_*",
        "sos_commands/systemd/systemctl_status_--all",
    ]

    def __init__(self, parser, parsed_args, cmdline_args):
        self.parser = parser
        self.args = parsed_args
        self.cmdline = cmdline_args
        self.exit_process = False
        self.archive = None
        self.tmpdir = None
        self.tempfile_util = None
        self.manifest = None

        try:
            import signal
            signal.signal(signal.SIGTERM, self.get_exit_handler())
        except Exception as err:
            sys.stdout.write(f"Notice: Could not set SIGTERM handler: {err}\n")

        self.opts = SoSOptions(arg_defaults=self._arg_defaults)
        if self.load_policy:
            self.load_local_policy()

        # update args from component's arg_defaults definition
        self._arg_defaults.update(self.arg_defaults)
        self.opts = self.load_options()  # lgtm [py/init-calls-subclass]

        if self.configure_logging:
            tmpdir = self.get_tmpdir_default()
            # only setup metadata if we are logging
            self.manifest = SoSMetadata()

            if not os.path.isdir(tmpdir) \
                    or not os.access(tmpdir, os.W_OK):
                msg = f"temporary directory {tmpdir} "
                msg += "does not exist or is not writable\n"
                # write directly to stderr as logging is not initialised yet
                sys.stderr.write(msg)
                self._exit(1)

            self.sys_tmp = tmpdir

            self.tmpdir = tempfile.mkdtemp(prefix="sos.", dir=self.sys_tmp)
            self.tempfile_util = TempFileUtil(self.tmpdir)
            self._setup_logging()

        if self.manifest is not None:
            self.manifest.add_field('version', __version__)
            self.manifest.add_field('cmdline', ' '.join(self.cmdline))
            self.manifest.add_field('start_time', datetime.now())
            # these three will be set later, add here for organization
            self.manifest.add_field('end_time', '')
            self.manifest.add_field('run_time', '')
            self.manifest.add_field('compression', '')
            self.manifest.add_field('tmpdir', self.tmpdir)
            self.manifest.add_field('tmpdir_fs_type', self.tmpfstype)
            self.manifest.add_field('policy', self.policy.distro)
            self.manifest.add_section('components')

    def load_local_policy(self):
        try:
            import sos.policies
            self.policy = sos.policies.load(sysroot=self.opts.sysroot,
                                            probe_runtime=self.load_probe)
            self.sysroot = self.policy.sysroot
        except KeyboardInterrupt:
            self._exit(0)
        self._is_root = self.policy.is_root()

    def execute(self):
        raise NotImplementedError

    def get_exit_handler(self):
        def exit_handler(signum, frame):
            self.exit_process = True
            self._exit()
        return exit_handler

    def _exit(self, error=0, msg=None):
        if msg:
            self.ui_log.error("")
            self.ui_log.error(msg)
        raise SystemExit(error)

    def get_tmpdir_default(self):
        """If --tmp-dir is not specified, provide a default location.
        Normally this is /var/tmp, but if we detect we are in a container, then
        use a standardized env var to redirect to the host's filesystem instead
        """
        if self.opts.tmp_dir:
            tmpdir = os.path.abspath(self.opts.tmp_dir)
        else:
            tmpdir = os.getenv('TMPDIR', None) or '/var/tmp'

        if os.getenv('HOST', None) and os.getenv('container', None):
            tmpdir = os.path.join(os.getenv('HOST'), tmpdir.lstrip('/'))

        # no standard library method exists for this, so call out to stat to
        # avoid bringing in a dependency on psutil
        self.tmpfstype = shell_out(
            f"stat --file-system --format=%T {tmpdir}"
        ).strip()

        if self.tmpfstype == 'tmpfs':
            # can't log to the ui or sos.log yet since those require a defined
            # tmpdir to setup
            print("WARNING: tmp-dir is set to a tmpfs filesystem. This may "
                  "increase memory pressure and cause instability on low "
                  "memory systems, or when using --all-logs.")
            time.sleep(2)

        return tmpdir

    def check_listing_options(self):
        opts = [o for o in self.opts.dict().keys() if o.startswith('list')]
        if opts:
            return any([getattr(self.opts, opt) for opt in opts])
        return False

    @classmethod
    def add_parser_options(cls, parser):
        """This should be overridden by each subcommand to add its own unique
        options to the parser
        """
        pass

    def apply_options_from_cmdline(self, opts):
        """(Re-)apply options specified via the cmdline to an options instance

        There are several cases where we may need to re-apply the options from
        the cmdline over previously loaded options - for instance when an
        option is specified in both a config file and cmdline, or a preset and
        the cmdline, or all three.

        Use this to re-apply cmdline option overrides to anything that may
        change the default values of options

        Positional arguments:

            :param opts:        SoSOptions object to update

        """
        # override the values from config files with the values from the
        # cmdline iff that value was explicitly specified, and compare it to
        # the _current_ set of opts from the config files as a default
        cmdopts = SoSOptions().from_args(
            self.parser.parse_args(self.cmdline),
            arg_defaults=opts.dict(preset_filter=False)
        )
        # we can't use merge() here, as argparse will pass default values for
        # unset options which would effectively negate config file settings and
        # set all values back to their normal default
        codict = cmdopts.dict(preset_filter=False)
        for opt, val in codict.items():
            if opt not in cmdopts.arg_defaults.keys() or val in [None, [], '']:
                continue
            # A plugin that is [enabled|disabled|only] in cmdopts must
            # overwrite these three options of itself in opts - reset it first
            if opt in ["enable_plugins", "skip_plugins", "only_plugins"]:
                for oopt in ["enable_plugins", "skip_plugins", "only_plugins"]:
                    common = set(val) & set(getattr(opts, oopt))
                    # common has all plugins that are in this combination of
                    # "[-e|-o|-n] plug" of cmdopts & "[-e|-o|-n] plug" of opts
                    # so remove those plugins from this [-e|-o|-n] opts
                    if common:
                        setattr(opts, oopt, [x for x in getattr(opts, oopt)
                                if x not in common])

            if val != opts.arg_defaults[opt]:
                setattr(opts, opt, val)

        return opts

    def load_options(self):
        """Compile arguments loaded from defaults, config files, and the
        command line into a usable set of options
        """
        # load the defaults defined by the component and the shared options
        opts = SoSOptions(arg_defaults=self._arg_defaults)

        for option in self.parser._actions:
            if option.default != SUPPRESS:
                option.default = None

        opts.update_from_conf(self.args.config_file, self.args.component)

        # directly check the cmdline options here as they have yet to be loaded
        # as SoSOptions, and if we do this check after they are loaded we would
        # need to do a second update from cmdline options for overriding config
        # file values
        if '--clean' in self.cmdline or '--mask' in self.cmdline:
            opts.update_from_conf(self.args.config_file, 'clean')

        if os.getuid() != 0:
            userconf = os.path.join(Path.home(), '.config/sos/sos.conf')
            if os.path.exists(userconf):
                opts.update_from_conf(userconf, self.args.component)

        opts = self.apply_options_from_cmdline(opts)

        # user specified command line preset
        self.preset = None
        if hasattr(opts, 'preset'):
            if opts.preset != self._arg_defaults["preset"]:
                self.preset = self.policy.find_preset(opts.preset)
                if not self.preset:
                    sys.stderr.write(f"Unknown preset: '{opts.preset}'\n")
                    self.preset = self.policy.probe_preset()
                    opts.list_presets = True

            # --preset=auto
            if not self.preset:
                self.preset = self.policy.probe_preset()
            # now merge preset options to opts
            opts.merge(self.preset.opts)
            # re-apply any cmdline overrides to the preset
            opts = self.apply_options_from_cmdline(opts)

            if hasattr(self.preset.opts, 'verbosity') and \
                    self.preset.opts.verbosity > 0:
                self.set_loggers_verbosity(self.preset.opts.verbosity)

        return opts

    def cleanup(self):
        # archive and tempfile cleanup may fail due to a fatal
        # OSError exception (ENOSPC, EROFS etc.).
        try:
            if self.archive:
                self.archive.cleanup()
            if self.tempfile_util:
                self.tempfile_util.clean()
            if self.tmpdir:
                rmtree(self.tmpdir)
        except Exception as err:
            print(f"Failed to finish cleanup: {err}\nContents may remain in "
                  f"{self.tmpdir}")

    def _set_encrypt_from_env_vars(self):
        msg = ('No encryption environment variables set, archive will not be '
               'encrypted')
        if os.environ.get('SOSENCRYPTKEY'):
            self.opts.encrypt_key = os.environ.get('SOSENCRYPTKEY')
            msg = 'Encryption key set via environment variable'
        elif os.environ.get('SOSENCRYPTPASS'):
            self.opts.encrypt_pass = os.environ.get('SOSENCRYPTPASS')
            msg = 'Encryption passphrase set via environment variable'
        self.soslog.info(msg)
        self.ui_log.info(msg)

    def _get_encryption_method(self):
        if not self.opts.batch:
            _enc = None
            while _enc not in ('P', 'K', 'E', 'N'):
                _enc = input((
                    'Specify encryption method [P]assphrase, [K]ey, [E]nv '
                    'vars, [N]o encryption: '
                )).upper()
            if _enc == 'P':
                self.opts.encrypt_pass = getpass('Specify encryption '
                                                 'passphrase: ')
            elif _enc == 'K':
                self.opts.encrypt_key = input('Specify encryption key: ')
            elif _enc == 'E':
                self._set_encrypt_from_env_vars()
            else:
                self.opts.encrypt_key = None
                self.opts.encrypt_pass = None
                self.soslog.info("User specified --encrypt, but chose no "
                                 "encryption when prompted.")
                self.ui_log.warning("Archive will not be encrypted")
        else:
            self._set_encrypt_from_env_vars()

    def setup_archive(self, name=''):
        if self.opts.encrypt:
            self._get_encryption_method()
        enc_opts = {
            'encrypt': True if (self.opts.encrypt_pass or
                                self.opts.encrypt_key) else False,
            'key': self.opts.encrypt_key,
            'password': self.opts.encrypt_pass
        }
        if not name:
            name = self.policy.get_archive_name()
        archive_name = os.path.join(self.tmpdir, name)
        if self.opts.compression_type == 'auto':
            auto_archive = self.policy.get_preferred_archive()
            self.archive = auto_archive(archive_name, self.tmpdir,
                                        self.policy, self.opts.threads,
                                        enc_opts, self.sysroot,
                                        self.manifest)

        else:
            self.archive = TarFileArchive(archive_name, self.tmpdir,
                                          self.policy, self.opts.threads,
                                          enc_opts, self.sysroot,
                                          self.manifest)

        self.archive.set_debug(self.opts.verbosity > 2)

    def _obfuscate_upload_passwords(self):
        # obfuscate strings like:
        # --upload-pass=PASSWORD
        # --upload-pass PASSWORD
        # --upload-url https://user:PASSWORD@some.url
        # in both sos_logs/sos.log and in sos_reports/manifest.json
        # and several sos_commands/* places from plugins's collected data
        _arc_path = self.archive.get_archive_path()
        for path in self.files_with_upload_passwd:
            for f in Path(_arc_path).glob(path):
                # get just the relative path that archive works with
                f = os.path.relpath(f, _arc_path)
                for re in [r"(--upload-pass[\s=]+)\S+",
                           r"(--upload-url[\s=]+\S+://.*:)([^@]*)",
                           r"(--upload-s3-secret-key[\s=]+)\S+"]:
                    self.archive.do_file_sub(f, re, r"\1********")

    def add_ui_log_to_stdout(self):
        ui_console = logging.StreamHandler(sys.stdout)
        ui_console.setFormatter(logging.Formatter('%(message)s'))
        ui_console.setLevel(
            logging.DEBUG if self.opts.verbosity > 1 else logging.INFO
        )
        self.ui_log.addHandler(ui_console)

    def set_loggers_verbosity(self, verbosity):
        if getattr(self, 'flog', None) and verbosity:
            self.flog.setLevel(logging.DEBUG)
        if getattr(self, 'console', None):
            if verbosity and self.opts.verbosity > 1:
                self.console.setLevel(logging.DEBUG)
            else:
                self.console.setLevel(logging.WARNING)

    def _setup_logging(self):
        """Creates the log handler that shall be used by all components and any
        and all related bits to those components that need to log either to the
        console or to the log file for that run of sos.
        """
        # main soslog
        self.soslog = logging.getLogger('sos')
        self.soslog.setLevel(logging.DEBUG)
        self.flog = None
        if not self.check_listing_options():
            self.sos_log_file = self.get_temp_file()
            self.flog = logging.StreamHandler(self.sos_log_file)
            self.flog.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s'))
            self.flog.setLevel(logging.INFO)
            self.soslog.addHandler(self.flog)

        if not self.opts.quiet:
            self.console = logging.StreamHandler(sys.stdout)
            self.console.setFormatter(logging.Formatter('%(message)s'))
            self.set_loggers_verbosity(self.opts.verbosity)
            self.soslog.addHandler(self.console)
        # still log ERROR level message to console, but only setup this handler
        # when --quiet is used, as otherwise we'll double log
        else:
            console_err = logging.StreamHandler(sys.stderr)
            console_err.setFormatter(logging.Formatter('%(message)s'))
            console_err.setLevel(logging.ERROR)
            self.soslog.addHandler(console_err)

        # ui log
        self.ui_log = logging.getLogger('sos_ui')
        self.ui_log.setLevel(
            logging.DEBUG if self.opts.verbosity > 1 else logging.INFO
        )
        if not self.check_listing_options():
            self.sos_ui_log_file = self.get_temp_file()
            ui_fhandler = logging.StreamHandler(self.sos_ui_log_file)
            ui_fhandler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s'))

            self.ui_log.addHandler(ui_fhandler)

        if not self.opts.quiet:
            self.add_ui_log_to_stdout()

    def get_temp_file(self):
        return self.tempfile_util.new()


class SoSMetadata():
    """This class is used to record metadata from a sos execution that will
    then be stored as a JSON-formatted manifest within the final tarball.

    It can be extended by adding further instances of SoSMetadata to represent
    dict-like structures throughout the various sos bits that record to
    metadata
    """

    def __init__(self):
        self._values = {}

    def __iter__(self):
        for item in self._values.items():
            yield item[1]

    def __getitem__(self, item):
        return self._values[item]

    def __getattr__(self, attr):
        try:
            return self._values[attr]
        except Exception:
            raise AttributeError(attr)

    def add_field(self, field_name, content):
        """Add a key, value entry to the current metadata instance
        """
        self._values[field_name] = content

    def add_section(self, section_name):
        """Adds a new instance of SoSMetadata to the current instance
        """
        self._values[section_name] = SoSMetadata()
        return self._values[section_name]

    def add_list(self, list_name, content=[]):
        """Add a named list element to the current instance. If content is not
        supplied, then add an empty list that can alter be appended to
        """
        if not isinstance(content, list):
            raise TypeError('content added must be list')
        self._values[list_name] = content

    def get_json(self, indent=None):
        """Convert contents of this SoSMetdata instance, and all other nested
        instances (sections), into a json-formatted output.

        Used to write manifest.json to the final archives.
        """
        return json.dumps(self,
                          default=lambda o: getattr(o, '_values', str(o)),
                          indent=indent)

# vim: set et ts=4 sw=4 :
