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
import os

class pxe(sos.plugintools.PluginBase):
    """PXE related information
    """

    optionList = [("tftpboot", 'gathers content in /tftpboot', 'slow', False)]

    def checkenabled(self):
        if self.cInfo["policy"].pkgByName("system-config-netboot-cmd") or os.path.exists("/usr/sbin/pxeos"):
            return True
        return False
        
    def setup(self):
        self.collectExtOutput("/usr/sbin/pxeos -l")
        self.addCopySpec("/etc/dhcpd.conf")
        if self.getOption("tftpboot"):
            self.addCopySpec("/tftpboot")
        return
