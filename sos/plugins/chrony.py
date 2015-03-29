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


class Chrony(Plugin, RedHatPlugin):
    """Chrony clock (for Network time protocol)
    """

    plugin_name = "chrony"
    profiles = ('system', 'services')

    packages = ('chrony',)

    def setup(self):
        self.add_copy_spec([
            "/etc/chrony.conf",
            "/var/lib/chrony/drift"
        ])
        self.add_cmd_output([
            "chronyc tracking",
            "chronyc sources",
            "chronyc sourcestats",
            "chronyc clients",
            "journalctl -u chronyd"
        ])

# vim: et ts=4 sw=4
