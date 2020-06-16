# Copyright 2010 Red Hat, Inc.
# Author: Adam Stokes <astokes@fedoraproject.org>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


"""
This module houses the i18n setup and message function. The default is to use
gettext to internationalize messages.
"""
__version__ = "3.9"

import six

from argparse import ArgumentParser

if six.PY3:
    from configparser import ConfigParser, ParsingError, Error
else:
    from ConfigParser import ConfigParser, ParsingError, Error

from sos.report import SoSReport

# Global option definitions
# These must be in the module itself in order to be available to both
# the sosreport and policy module (and to avoid recursive import errors).
#
# FIXME: these definitions make our main module a bit more bulky: the
# alternative is to place these in a new sos.options module. This may
# prove to be the best route long-term (as it could also contain an
# exported parsing routine, and all the command-line definitions).

#: Names of all arguments
_arg_names = [
    'add_preset', 'alloptions', 'allow_system_changes', 'all_logs', 'batch',
    'build', 'case_id', 'chroot', 'compression_type', 'config_file', 'desc',
    'debug', 'del_preset', 'dry_run', 'enableplugins', 'encrypt_key',
    'encrypt_pass', 'experimental', 'label', 'list_plugins', 'list_presets',
    'list_profiles', 'log_size', 'noplugins', 'noreport', 'no_env_vars',
    'no_postproc', 'note', 'onlyplugins', 'plugin_timeout', 'plugopts',
    'preset', 'profiles', 'quiet', 'since', 'sysroot', 'threads', 'tmp_dir',
    'upload', 'upload_url', 'upload_directory', 'upload_user', 'upload_pass',
    'verbosity', 'verify'
]

#: Arguments with non-zero default values
_arg_defaults = {
    "chroot": "auto",
    "compression_type": "auto",
    "log_size": 25,
    "preset": "auto",
    # Verbosity has an explicit zero default since the ArgumentParser
    # count action default is None.
    "verbosity": 0
}


def _is_seq(val):
    """Return true if val is an instance of a known sequence type.
    """
    val_type = type(val)
    return val_type is list or val_type is tuple


class SoSOptions(object):

    def _merge_opt(self, opt, src, is_default):
        def _unset(val):
            return (val == "" or val is None)

        if hasattr(src, opt):
            newvalue = getattr(src, opt)
            oldvalue = getattr(self, opt)
            # overwrite value iff:
            # - we replace unset option by a real value
            # - new default is set, or
            # - non-sequential variable keeps its default value
            if (_unset(oldvalue) and not _unset(newvalue)) or \
               is_default or \
               ((opt not in self._nondefault) and (not _is_seq(newvalue))):
                # Overwrite atomic values
                setattr(self, opt, newvalue)
                if is_default:
                    self._nondefault.discard(opt)
                else:
                    self._nondefault.add(opt)
            elif _is_seq(newvalue):
                # Concatenate sequence types
                setattr(self, opt, newvalue + oldvalue)

    def _merge_opts(self, src, is_default):
        for arg in _arg_names:
            self._merge_opt(arg, src, is_default)

    def __str(self, quote=False, sep=" ", prefix="", suffix=""):
        """Format a SoSOptions object as a human or machine readable string.

            :param quote: quote option values
            :param sep: list separator string
            :param prefix: arbitrary prefix string
            :param suffix: arbitrary suffix string
            :param literal: print values as Python literals
        """
        args = prefix
        arg_fmt = "=%s"
        for arg in _arg_names:
            args += arg + arg_fmt + sep
        args.strip(sep)

        vals = [getattr(self, arg) for arg in _arg_names]
        if not quote:
            # Convert Python source notation for sequences into plain strings
            vals = [",".join(v) if _is_seq(v) else v for v in vals]
        else:
            def is_string(val):
                return isinstance(val, six.string_types)
            # Only quote strings if quote=False
            vals = ["'%s'" % v if is_string(v) else v for v in vals]

        return (args % tuple(vals)).strip(sep) + suffix

    def __str__(self):
        return self.__str()

    def __repr__(self):
        return self.__str(quote=True, sep=", ", prefix="SoSOptions(",
                          suffix=")")

    def __init__(self, **kwargs):
        """Initialise a new ``SoSOptions`` object from keyword arguments.

            Initialises the new object with values taken from keyword
            arguments matching the names of ``SoSOptions`` attributes.

            A ``ValueError`` is raised is any of the supplied keyword
            arguments does not correspond to a known ``SoSOptions`
            attribute name.

            :param *kwargs: a list of ``SoSOptions`` keyword args.
            :returns: the new ``SoSOptions`` object.
        """
        self.add_preset = ""
        self.alloptions = False
        self.all_logs = False
        self.since = None
        self.batch = False
        self.build = False
        self.case_id = ""
        self.chroot = _arg_defaults["chroot"]
        self.compression_type = _arg_defaults["compression_type"]
        self.config_file = ""
        self.debug = False
        self.del_preset = ""
        self.desc = ""
        self.dry_run = False
        self.enableplugins = []
        self.encrypt_key = None
        self.encrypt_pass = None
        self.experimental = False
        self.label = ""
        self.list_plugins = False
        self.list_presets = False
        self.list_profiles = False
        self.log_size = _arg_defaults["log_size"]
        self.noplugins = []
        self.noreport = False
        self.allow_system_changes = False
        self.no_env_vars = False
        self.no_postproc = False
        self.note = ""
        self.onlyplugins = []
        self.plugin_timeout = None
        self.plugopts = []
        self.preset = _arg_defaults["preset"]
        self.profiles = []
        self.quiet = False
        self.sysroot = None
        self.threads = 4
        self.tmp_dir = ""
        self.upload = False
        self.upload_url = ""
        self.upload_directory = ""
        self.upload_user = ""
        self.upload_pass = ""
        self.verbosity = _arg_defaults["verbosity"]
        self.verify = False
        self._nondefault = set()
        for arg in kwargs.keys():
            if arg not in _arg_names:
                raise ValueError("Unknown SoSOptions attribute: %s" % arg)
            setattr(self, arg, kwargs[arg])

    @classmethod
    def from_args(cls, args):
        """Initialise a new SoSOptions object from a ``Namespace``
            obtained by parsing command line arguments.

            :param args: parsed command line arguments
            :returns: an initialised SoSOptions object
            :returntype: SoSOptions
        """
        opts = SoSOptions()
        opts._merge_opts(args, True)
        return opts

    @classmethod
    def _opt_to_args(cls, opt, val):
        """Convert a named option and optional value to command line
            argument notation, correctly handling options that take
            no value or that have special representations (e.g. verify
            and verbose).
        """
        no_value = (
            "alloptions", "allow-system-changes", "all-logs", "batch", "build",
            "debug", "experimental", "list-plugins", "list-presets",
            "list-profiles", "no-report", "no-env-vars", "quiet", "verify"
        )
        count = ("verbose",)
        if opt in no_value:
            return ["--%s" % opt]
        if opt in count:
            return ["--%s" % opt for d in range(0, int(val))]
        return ["--" + opt + "=" + val]

    @classmethod
    def from_file(cls, argparser, config_file, is_default=True):
        opts = SoSOptions()
        config = ConfigParser()
        try:
            try:
                with open(config_file) as f:
                    config.readfp(f)
            except (ParsingError, Error) as e:
                raise exit('Failed to parse configuration '
                           'file %s' % config_file)
        except (OSError, IOError) as e:
            raise exit('Unable to read configuration file %s '
                       ': %s' % (config_file, e.args[1]))

        if config.has_section("general"):
            optlist = []
            for opt, val in config.items("general"):
                optlist.extend(SoSOptions._opt_to_args(opt, val))
            opts._merge_opts(argparser.parse_args(optlist), is_default)

        opts.noplugins = []
        if config.has_option("plugins", "disable"):
            opts.noplugins.extend([plugin.strip() for plugin in
                                  config.get("plugins", "disable").split(',')])

        if config.has_option("plugins", "enable"):
            opts.enableplugins = []
            opts.enableplugins.extend(
                    [plugin.strip() for plugin in
                     config.get("plugins", "enable").split(',')])

        if config.has_section("tunables"):
            opts.plugopts = []
            for opt, val in config.items("tunables"):
                if not opt.split('.')[0] in opts.noplugins:
                    opts.plugopts.append(opt + "=" + val)

        return opts

    def merge(self, src, skip_default=True):
        """Merge another set of ``SoSOptions`` into this object.

            Merge two ``SoSOptions`` objects by setting unset or default
            values to their value in the ``src`` object.

            :param src: the ``SoSOptions`` object to copy from
            :param is_default: ``True`` if new default values are to be set.
        """
        for arg in _arg_names:
            if not hasattr(src, arg):
                continue
            if getattr(src, arg) is not None or not skip_default:
                self._merge_opt(arg, src, False)

    def dict(self):
        """Return this ``SoSOptions`` option values as a dictionary of
            argument name to value mappings.

            :returns: a name:value dictionary of option values.
        """
        odict = {}
        for arg in _arg_names:
            value = getattr(self, arg)
            # Do not attempt to store preset option values in presets
            if arg in ('add_preset', 'del_preset', 'desc', 'note'):
                value = None
            odict[arg] = value
        return odict

    def to_args(self):
        """Return command arguments for this object.

            Return a list of the non-default options of this ``SoSOptions``
            object in ``sosreport`` command line argument notation:

                ``["--all-logs", "-vvv"]``

        """
        def has_value(name, value):
            """ Test for non-null option values.
            """
            null_values = ("False", "None", "[]", '""', "''", "0")
            if not value or value in null_values:
                return False
            if name in _arg_defaults:
                if str(value) == str(_arg_defaults[name]):
                    return False
            return True

        def filter_opt(name, value):
            """ Filter out preset and null-valued options.
            """
            if name in ("add_preset", "del_preset", "desc", "note"):
                return False
            return has_value(name, value)

        def argify(name, value):
            """ Convert sos option notation to command line arguments.
            """
            # Handle --verbosity specially
            if name.startswith("verbosity"):
                arg = "-" + int(value) * "v"
                return arg

            name = name.replace("_", "-")

            value = ",".join(value) if _is_seq(value) else value

            if value is not True:
                opt = "%s %s" % (name, value)
            else:
                opt = name

            arg = "--" + opt if len(opt) > 1 else "-" + opt
            return arg

        opt_items = sorted(self.dict().items(), key=lambda x: x[0])
        return [argify(n, v) for (n, v) in opt_items if filter_opt(n, v)]


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

    def __init__(self, parser, parsed_args, cmdline_args):
        self.parser = parser
        self.args = parsed_args
        self.cmdline = cmdline_args

class SoS():
    """Main entrypoint for sos from the command line

    Upon intialization, this class loads the basic option parser which will
    include the options shared by support components/subcommands. This is also
    where all subcommands present in the local installation are discovered,
    loaded, and if a matching one is found, intialized.
    """

    def __init__(self, args):
        self.cmdline = args
        usage_string = "%(prog)s component [options]\n\n"
        # define the local subcommands that exist on the system
        self._components = {'report': SoSReport}
        # build the top-level parser
        self.parser = ArgumentParser(usage=usage_string)
        self.parser.register('action', 'extend', SoSListOption)
        # set the component subparsers
        self.subparsers = self.parser.add_subparsers(
            dest='component',
            help='sos component to run'
        )
        self.subparsers.required = True
        # now build the parser for each component.
        # this needs to be done here, as otherwise --help will be unavailable
        # for the component subparsers
        for comp in self._components:
            _com_subparser = self.subparsers.add_parser(comp)
            _com_subparser.register('action', 'extend', SoSListOption)
            self._add_common_options(_com_subparser)
            self._components[comp].add_parser_options(_com_subparser)
        self.args = self.parser.parse_args()
        self._init_component()

    def _add_common_options(self, parser):
        """Adds the options shared across components to the parser
        """
        parser.add_argument("-q", "--quiet", action="store_true",
                            dest="quiet", default=False,
                            help="only print fatal errors")
        parser.add_argument("-s", "--sysroot", action="store", dest="sysroot",
                            help="system root directory path (default='/')",
                            default=None)
        parser.add_argument("--tmp-dir", action="store",
                            dest="tmp_dir",
                            help="specify alternate temporary directory",
                            default=None)
        parser.add_argument("-v", "--verbose", action="count",
                            dest="verbosity", default=0,
                            help="increase verbosity")

    def _init_component(self):
        """Determine which component has been requested by the user, and then
        initialize that component.
        """
        _com = self.args.component
        if not _com in self._components.keys():
            print("Unknown subcommand '%s' specified" % _com)
        try:
            self._component = self._components[_com](self.parser, self.args,
                                                     self.cmdline)
        except Exception as err:
            print("Could not initialize '%s': %s" % (_com, err))
            sys.exit(1)

# vim: set et ts=4 sw=4 :
