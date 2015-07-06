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


class Pxe(Plugin):
    """PXE service
    """
    plugin_name = "pxe"
    profiles = ('sysmgmt', 'network')
    option_list = [("tftpboot", 'gathers content from the tftpboot path',
                    'slow', False)]


class RedHatPxe(Pxe, RedHatPlugin):

    files = ('/usr/sbin/pxeos',)
    packages = ('system-config-netboot-cmd',)

    def setup(self):
        super(RedHatPxe, self).setup()
        self.add_cmd_output("/usr/sbin/pxeos -l")
        self.add_copy_spec("/etc/dhcpd.conf")
        if self.get_option("tftpboot"):
            self.add_copy_spec("/tftpboot")


class DebianPxe(Pxe, DebianPlugin, UbuntuPlugin):

    packages = ('tftpd-hpa',)

    def setup(self):
        super(DebianPxe, self).setup()
        self.add_copy_spec([
            "/etc/dhcp/dhcpd.conf",
            "/etc/default/tftpd-hpa"
        ])
        if self.get_option("tftpboot"):
            self.add_copy_spec("/var/lib/tftpboot")

# vim: set et ts=4 sw=4 :
