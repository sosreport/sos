# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Memory(Plugin, IndependentPlugin):

    short_desc = 'Memory configuration and use'

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
            "/sys/kernel/mm/transparent_hugepage/enabled",
            "/sys/kernel/mm/hugepages"
        ])
        self.add_cmd_output("free", root_symlink="free")
        self.add_cmd_output([
            "free -m",
            "swapon --bytes --show",
            "swapon --summary --verbose",
            "lsmem -a -o RANGE,SIZE,STATE,REMOVABLE,ZONES,NODE,BLOCK"
        ])

        # slabtop -o will hang if not handed a tty via stdin
        self.add_cmd_output("slabtop -o", foreground=True)

# vim: set et ts=4 sw=4 :
