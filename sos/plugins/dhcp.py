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

import sos.plugintools

class dhcp(sos.plugintools.PluginBase):
    """DHCP related information
    """
    def checkenabled(self):
        self.files = ['/etc/rc.d/init.d/dhcpd']
        self.packages = ['dhcp']
        return sos.plugintools.PluginBase.checkenabled(self)
        
    def setup(self):
        self.addCopySpec("/etc/sysconfig/dhcrelay")
        self.addCopySpec("/etc/sysconfig/dhcpd")
        self.addCopySpec("/etc/dhcpd.conf")
        self.addCopySpec("/etc/dhcp")
        return
