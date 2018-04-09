# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Hardware(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """General hardware information
    """

    plugin_name = "hardware"
    profiles = ('system', 'hardware')

    def setup(self):
        self.add_copy_spec([
            "/proc/interrupts",
            "/proc/irq",
            "/proc/dma",
            "/proc/devices",
            "/proc/rtc",
            "/var/log/mcelog",
            "/sys/class/dmi/id/*"
        ])

        self.add_cmd_output("dmidecode", root_symlink="dmidecode")


# vim: set et ts=4 sw=4 :
