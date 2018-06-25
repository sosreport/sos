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

import gettext
import six

__version__ = "3.6"

gettext_dir = "/usr/share/locale"
gettext_app = "sos"

gettext.bindtextdomain(gettext_app, gettext_dir)


def _default(msg):
    return gettext.dgettext(gettext_app, msg)


_sos = _default

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
    'add_preset', 'alloptions', 'all_logs', 'batch', 'build', 'case_id',
    'chroot', 'compression_type', 'config_file', 'desc', 'debug', 'del_preset',
    'enableplugins', 'experimental', 'label', 'list_plugins', 'list_presets',
    'list_profiles', 'log_size', 'noplugins', 'noreport', 'note',
    'onlyplugins', 'plugopts', 'preset', 'profiles', 'quiet', 'sysroot',
    'threads', 'tmp_dir', 'verbosity', 'verify'
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
    add_preset = ""
    alloptions = False
    all_logs = False
    batch = False
    build = False
    case_id = ""
    chroot = _arg_defaults["chroot"]
    compression_type = _arg_defaults["compression_type"]
    config_file = ""
    debug = False
    del_preset = ""
    desc = ""
    enableplugins = []
    experimental = False
    label = ""
    list_plugins = False
    list_presets = False
    list_profiles = False
    log_size = _arg_defaults["log_size"]
    noplugins = []
    noreport = False
    note = ""
    onlyplugins = []
    plugopts = []
    preset = ""
    profiles = []
    quiet = False
    sysroot = None
    threads = 4
    tmp_dir = ""
    verbosity = 0
    verify = False

    def _merge_opt(self, opt, src, replace):
        if hasattr(src, opt):
            value = getattr(src, opt)
            if replace or not _is_seq(value):
                # Overwrite atomic values
                setattr(self, opt, getattr(src, opt))
            else:
                # Concatenate sequence types
                setattr(self, opt, getattr(self, opt) + getattr(src, opt))

    def _merge_opts(self, src, replace):
        for arg in _arg_names:
            self._merge_opt(arg, src, replace)

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

    def merge(self, src, replace=False):
        """Merge another set of ``SoSOptions`` into this object.

            Merge two ``SoSOptions`` objects by setting unset or default
            values to their value in the ``src`` object.

            :param src: the ``SoSOptions`` object to copy from
            :param replace: ``True`` if non-default values should be
                            overwritten.
        """
        for arg in _arg_names:
            if not hasattr(src, arg):
                continue
            if _is_seq(getattr(self, arg)):
                self._merge_opt(arg, src, replace)
                continue
            if arg in _arg_defaults.keys():
                if replace or getattr(self, arg) == _arg_defaults[arg]:
                    self._merge_opt(arg, src, replace)
            else:
                if replace or not getattr(self, arg):
                    self._merge_opt(arg, src, replace)

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

# vim: set et ts=4 sw=4 :
