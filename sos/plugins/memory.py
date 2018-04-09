# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Memory(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Memory configuration and use
    """

    plugin_name = 'memory'
    profiles = ('system', 'hardware', 'memory')

    def setup(self):
        self.add_copy_spec([
            "/proc/pci",
            "/proc/meminfo",
            "/proc/vmstat",
            "/proc/swaps",
            "/proc/slabinfo",
            "/proc/pagetypeinfo",
            "/proc/vmallocinfo",
            "/sys/kernel/mm/ksm",
            "/sys/kernel/mm/transparent_hugepage/enabled"
        ])
        self.add_cmd_output("free", root_symlink="free")
        self.add_cmd_output([
            "free -m",
            "swapon --bytes --show",
            "swapon --summary --verbose"
        ])

# vim: set et ts=4 sw=4 :
