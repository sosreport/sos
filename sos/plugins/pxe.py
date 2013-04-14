### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class pxe(Plugin, RedHatPlugin):
    """PXE related information
    """

    option_list = [("tftpboot", 'gathers content in /tftpboot', 'slow', False)]
    files = ('pxeos',)
    packages = ('system-config-netboot-cmd',)

    def setup(self):
        self.add_cmd_output("pxeos -l")
        self.add_copy_spec("/etc/dhcpd.conf")
        if self.get_option("tftpboot"):
            self.add_copy_spec("/tftpboot")
