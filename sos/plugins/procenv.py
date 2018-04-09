# Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, DebianPlugin, UbuntuPlugin


class Procenv(Plugin, DebianPlugin, UbuntuPlugin):
    """Process environment
    """

    plugin_name = 'procenv'
    profiles = ('system',)

    def setup(self):
        self.add_cmd_output('procenv')

# vim: set et ts=4 sw=4 :
