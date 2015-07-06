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

from sos.plugins import Plugin, RedHatPlugin


class VMWare(Plugin, RedHatPlugin):
    """VMWare client information
    """

    plugin_name = 'vmware'
    profiles = ('virt',)

    files = ('vmware', '/usr/init.d/vmware-tools')

    def setup(self):
        self.add_cmd_output("vmware -v")
        self.add_copy_spec([
            "/etc/vmware/locations",
            "/etc/vmware/config",
            "/proc/vmmemctl"
        ])

# vim: set et ts=4 sw=4 :
