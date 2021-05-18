# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Pci(Plugin, IndependentPlugin):

    short_desc = 'PCI devices'

    plugin_name = "pci"
    profiles = ('hardware', 'system')

    def check_for_bus_devices(self):
        if not self.path_isdir('/proc/bus/pci'):
            return False
        # ensure that more than just the 'devices' file, which can be empty,
        # exists in the pci directory. This implies actual devices are present
        content = self.listdir('/proc/bus/pci')
        if 'devices' in content:
            content.remove('devices')
        return len(content) > 0

    def setup(self):
        self.add_copy_spec([
            "/proc/ioports",
            "/proc/iomem",
            "/proc/bus/pci"
        ])

        if self.check_for_bus_devices():
            self.add_cmd_output("lspci -nnvv", root_symlink="lspci")
            self.add_cmd_output("lspci -tv")

# vim: set et ts=4 sw=4 :
