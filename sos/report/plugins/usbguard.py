# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class UsbGuard(Plugin, IndependentPlugin):

    short_desc = 'USB device usage policy'

    plugin_name = "usbguard"
    profiles = ('system',)
    packages = ('usbguard',)
    commands = ('usbguard',)

    def setup(self):
        self.add_copy_spec("/etc/usbguard")

        self.add_cmd_output([
            "usbguard list-devices",
            "usbguard list-rules"
        ])

# vim: set et ts=4 sw=4 :
