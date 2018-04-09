# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Usb(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """USB devices
    """

    plugin_name = "usb"
    profiles = ('hardware',)

    def setup(self):
        self.add_copy_spec("/sys/bus/usb")

        self.add_cmd_output([
            "lsusb",
            "lsusb -v",
            "lsusb -t"
        ])

# vim: set et ts=4 sw=4 :
