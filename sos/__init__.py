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
from collections import deque

__version__ = "3.5"

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
    'all_logs', 'batch', 'build', 'case_id', 'chroot', 'compression_type',
    'config_file', 'debug', 'enableplugins', 'experimental', 'label',
    'list_plugins', 'list_profiles', 'log_size', 'noplugins', 'noreport',
    'onlyplugins', 'plugopts', 'profiles', 'quiet', 'sysroot', 'tmp_dir',
    'usealloptions', 'verbosity', 'verify'
]

#: Arguments with non-zero default values
_arg_defaults = {
    "log_size": 10,
    "chroot": "auto",
    "compression_type": "auto",
}


class SoSOptions(object):
    list_plugins = False
    noplugins = []
    enableplugins = []
    onlyplugins = []
    plugopts = []
    usealloptions = False
    all_logs = False
    log_size = _arg_defaults["log_size"]
    batch = False
    build = False
    verbosity = 0
    verify = False
    quiet = False
    debug = False
    case_id = ""
    label = ""
    profiles = deque()
    list_profiles = False
    config_file = ""
    tmp_dir = ""
    noreport = False
    sysroot = None
    chroot = _arg_defaults["chroot"]
    compression_type = _arg_defaults["compression_type"]
    experimental = False
    threads = 4

    def _copy_opt(self, opt, src):
        if hasattr(src, opt):
            setattr(self, opt, getattr(src, opt))

    def _copy_opts(self, src):
        for arg in _arg_names:
            self._copy_opt(arg, src)

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
        opts._copy_opts(args)
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
            if arg in _arg_defaults.keys():
                if replace or getattr(self, arg) == _arg_defaults[arg]:
                    self._copy_opt(arg, src)
            else:
                if replace or not getattr(self, arg):
                    self._copy_opt(arg, src)

# vim: set et ts=4 sw=4 :
