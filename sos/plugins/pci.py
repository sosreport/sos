# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Pci(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """PCI devices
    """

    plugin_name = "pci"
    profiles = ('hardware', 'system')

    def setup(self):
        self.add_copy_spec([
            "/proc/ioports",
            "/proc/iomem",
            "/proc/bus/pci"
        ])

        self.add_cmd_output("lspci -nnvv", root_symlink="lspci")
        self.add_cmd_output("lspci -tv")

# vim: set et ts=4 sw=4 :
