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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Dhcp(Plugin):
    """DHCP daemon
    """

    plugin_name = "dhcp"
    profiles = ('network',)


class RedHatDhcp(Dhcp, RedHatPlugin):

    files = ('/etc/rc.d/init.d/dhcpd',)
    packages = ('dhcp',)

    def setup(self):
        super(RedHatDhcp, self).setup()
        self.add_copy_spec([
            "/etc/dhcpd.conf",
            "/etc/dhcp"
        ])


class UbuntuDhcp(Dhcp, UbuntuPlugin):

    files = ('/etc/init.d/udhcpd',)
    packages = ('udhcpd',)

    def setup(self):
        super(UbuntuDhcp, self).setup()
        self.add_copy_spec([
            "/etc/default/udhcpd",
            "/etc/udhcpd.conf"
        ])

# vim: set et ts=4 sw=4 :
