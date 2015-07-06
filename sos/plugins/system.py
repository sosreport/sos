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


class System(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """core system information
    """

    plugin_name = "system"
    profiles = ('system', 'kernel')

    def setup(self):
        self.add_copy_spec("/proc/sys")
        self.add_forbidden_path(
            "/proc/sys/net/ipv6/neigh/*/retrans_time")
        self.add_forbidden_path(
            "/proc/sys/net/ipv6/neigh/*/base_reachable_time")


# vim: set et ts=4 sw=4 :
