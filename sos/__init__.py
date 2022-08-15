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
__version__ = "4.4"

import os
import sys

from argparse import ArgumentParser
from sos.options import SosListOption

import gettext
gettext_dir = "/usr/share/locale"
gettext_app = "sos"
gettext.bindtextdomain(gettext_app, gettext_dir)


def _default(msg):
    return gettext.dgettext(gettext_app, msg)


_sos = _default

# py3 < 3.6 compat
try:
    ModuleNotFoundError
except NameError:
    ModuleNotFoundError = ImportError


class SoS():
    """Main entrypoint for sos from the command line

    Upon intialization, this class loads the basic option parser which will
    include the options shared by support components/subcommands. This is also
    where all subcommands present in the local installation are discovered,
    loaded, and if a matching one is found, intialized.
    """

    def __init__(self, args):
        self.cmdline = args
        # define the local subcommands that exist on the system
        # first import the necessary module, then add an entry to the dict that
        # follows the tuple format (class, [aliases]), where aliases is a list
        # of shorthand names to accept in place of the full subcommand
        # if no aliases are desired, pass an empty list
        import sos.report
        import sos.cleaner
        import sos.help
        self._components = {
            'report': (sos.report.SoSReport, ['rep']),
            'clean': (sos.cleaner.SoSCleaner, ['cleaner', 'mask']),
            'help': (sos.help.SoSHelper, [])
        }
        # some distros do not want pexpect as a default dep, so try to load
        # collector here, and if it fails add an entry that implies it is at
        # least present on this installation
        try:
            import sos.collector
            self._components['collect'] = (sos.collector.SoSCollector,
                                           ['collector'])
        except ModuleNotFoundError as err:
            import sos.missing
            if 'sos.collector' in err.msg:
                # is not locally installed - packaged separately
                self._components['collect'] = (sos.missing.MissingCollect, [])
            elif 'pexpect' in err.msg:
                # cannot be imported due to missing the pexpect dep
                self._components['collect'] = (sos.missing.MissingPexpect, [])
            else:
                # we failed elsewhere, re-raise the exception
                raise
        # build the top-level parser
        _com_string = ''
        for com in self._components:
            aliases = self._components[com][1]
            aliases.insert(0, com)
            _com = ', '.join(aliases)
            desc = self._components[com][0].desc
            _com_string += (
                "\t{com:<30}{desc}\n".format(com=_com, desc=desc)
            )
        usage_string = ("%(prog)s <component> [options]\n\n"
                        "Available components:\n")
        usage_string = usage_string + _com_string
        epilog = ("See `sos <component> --help` for more information")
        self.parser = ArgumentParser(usage=usage_string, epilog=epilog)
        self.parser.register('action', 'extend', SosListOption)
        # set the component subparsers
        self.subparsers = self.parser.add_subparsers(
            dest='component',
            metavar='component',
            help='sos component to run'
        )
        self.subparsers.required = True
        # now build the parser for each component.
        # this needs to be done here, as otherwise --help will be unavailable
        # for the component subparsers
        for comp in self._components:
            _com_subparser = self.subparsers.add_parser(
                comp,
                aliases=self._components[comp][1],
                prog="sos %s" % comp
            )
            _com_subparser.usage = "sos %s [options]" % comp
            _com_subparser.register('action', 'extend', SosListOption)
            self._add_common_options(_com_subparser)
            self._components[comp][0].add_parser_options(parser=_com_subparser)
            _com_subparser.set_defaults(component=comp)
        self.args = self.parser.parse_args(self.cmdline)
        self._init_component()

    def _add_common_options(self, parser):
        """Adds the options shared across components to the parser
        """
        global_grp = parser.add_argument_group('Global Options')
        global_grp.add_argument("--batch", default=False, action="store_true",
                                help="Do not prompt interactively")
        global_grp.add_argument("--config-file", type=str, action="store",
                                dest="config_file",
                                default="/etc/sos/sos.conf",
                                help="specify alternate configuration file")
        global_grp.add_argument("--debug", action="store_true", dest="debug",
                                help="enable interactive debugging using the "
                                     "python debugger")
        global_grp.add_argument("-q", "--quiet", action="store_true",
                                dest="quiet", default=False,
                                help="only print fatal errors")
        global_grp.add_argument("-s", "--sysroot", action="store",
                                dest="sysroot", default=None,
                                help="system rootdir path (default='/')")
        global_grp.add_argument("--tmp-dir", action="store", dest="tmp_dir",
                                default=None,
                                help="specify alternate temporary directory")
        global_grp.add_argument("-t", "--threads", action="store",
                                dest="threads", default=4, type=int,
                                help="Number of threads to use")
        global_grp.add_argument("-v", "--verbose", action="count",
                                dest="verbosity", default=0,
                                help="increase verbosity")

        global_grp.add_argument('-z', '--compression-type',
                                dest="compression_type",
                                choices=['auto', 'gzip', 'xz'],
                                help="compression technology to use")

        # Group to make tarball encryption (via GPG/password) exclusive
        encrypt_grp = global_grp.add_mutually_exclusive_group()
        encrypt_grp.add_argument("--encrypt", default=False,
                                 action="store_true",
                                 help=("Encrypt the archive, either prompting "
                                       "for a password/key or referencing "
                                       "an environment variable"))
        encrypt_grp.add_argument("--encrypt-key",
                                 help="Encrypt the archive using a GPG "
                                      "key-pair")
        encrypt_grp.add_argument("--encrypt-pass",
                                 help="Encrypt the archive using a password")

    def _init_component(self):
        """Determine which component has been requested by the user, and then
        initialize that component.
        """
        _com = self.args.component
        if _com not in self._components.keys():
            print("Unknown subcommand '%s' specified" % _com)
        try:
            _to_load = self._components[_com][0]
            if _to_load.root_required and not os.getuid() == 0:
                raise Exception("Component must be run with root privileges")
            self._component = _to_load(self.parser, self.args, self.cmdline)

        except Exception as err:
            print("Could not initialize '%s': %s" % (_com, err))
            if self.args.debug:
                raise err
            sys.exit(1)

    def execute(self):
        self._component.execute()

# vim: set et ts=4 sw=4 :
