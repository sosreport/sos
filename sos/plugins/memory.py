# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

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
            "swapon --bytes --show"
        ])

# vim: set et ts=4 sw=4 :
