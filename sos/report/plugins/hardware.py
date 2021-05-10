# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Hardware(Plugin, IndependentPlugin):

    short_desc = 'General hardware information'

    plugin_name = "hardware"
    profiles = ('system', 'hardware')

    def setup(self):

        self.add_copy_spec("/proc/interrupts", tags='interrupts')

        self.add_copy_spec([
            "/proc/irq",
            "/proc/dma",
            "/proc/devices",
            "/proc/rtc",
            "/var/log/mcelog",
            "/sys/class/dmi/id/*",
            "/sys/class/drm/*/edid"
        ])

        self.add_cmd_output("dmidecode", root_symlink="dmidecode")
        self.add_cmd_output("lshw")


# vim: set et ts=4 sw=4 :
