# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Wireless(Plugin, DebianPlugin, UbuntuPlugin):
    """Wireless
    """

    plugin_name = 'wireless'
    profiles = ('hardware', 'desktop', 'network')
    files = ('/sbin/iw', '/usr/sbin/iw')

    def setup(self):
        self.add_cmd_output([
            "iw list",
            "iw dev",
            "iwconfig",
            "iwlist scanning"
        ])


class RedHatWireless(Wireless, RedHatPlugin):
    """Wireless
    """

    files = ('/usr/sbin/iw', '/usr/sbin/iwlist')
    packages = ('iw', 'wireless-tools')

# vim: set et ts=4 sw=4 :
