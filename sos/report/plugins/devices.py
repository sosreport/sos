# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Devices(Plugin, IndependentPlugin):

    short_desc = 'devices specific commands'

    plugin_name = 'devices'
    profiles = ('system', 'hardware', 'boot', 'storage')
    packages = ('udev', 'systemd-udev')
    files = ('/dev',)

    def setup(self):
        self.add_cmd_output("udevadm info --export-db")

# vim: et ts=4 sw=4
