# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Devices(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ devices specific commands
    """

    plugin_name = 'devices'
    profiles = ('system', 'hardware', 'boot')
    packages = ('udev', 'systemd-udev')
    files = ('/dev',)

    def setup(self):
        self.add_cmd_output("udevadm info --export-db")

# vim: et ts=4 sw=4
