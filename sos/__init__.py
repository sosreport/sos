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

import logging
import six
import sys
import tempfile

from argparse import ArgumentParser
from sos.options import SosListOption

import gettext
gettext_dir = "/usr/share/locale"
gettext_app = "sos"
gettext.bindtextdomain(gettext_app, gettext_dir)

def _default(msg):
    return gettext.dgettext(gettext_app, msg)

_sos = _default


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
        import sos.report
        self._components = {'report': sos.report.SoSReport}
        # build the top-level parser
        _com_string = ''
        for com in self._components:
            _com_string += "\t%s\t\t\t%s\n" % (com, self._components[com].desc)
        usage_string = ("%(prog)s <component> [options]\n\n"
                        "Available components:\n")
        usage_string = usage_string + _com_string
        epilog = ("See `sos <component> --help` for more information")
        self.parser = ArgumentParser(usage=usage_string, epilog=epilog)
        self.parser.register('action', 'extend', SosListOption)
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
            _com_subparser.usage = "sos %s [options]" % comp
            _com_subparser.register('action', 'extend', SosListOption)
            self._add_common_options(_com_subparser)
            self._components[comp].add_parser_options(parser=_com_subparser)
        self.args = self.parser.parse_args()
        self._init_component()

    def _add_common_options(self, parser):
        """Adds the options shared across components to the parser
        """
        parser.add_argument("--config-file", type=str, action="store",
                            dest="config_file", default="/etc/sos.conf",
                            help="specify alternate configuration file")
        parser.add_argument("--debug", action="store_true", dest="debug",
                    help="enable interactive debugging using the "
                         "python debugger")
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
        parser.add_argument("-t", "--threads", action="store", dest="threads",
                            default=4, type=int,
                            help="Number of threads to use")
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

    def execute(self):
        self._component.execute()

# vim: set et ts=4 sw=4 :
