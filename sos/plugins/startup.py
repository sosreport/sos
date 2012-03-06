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

class startup(sos.plugintools.PluginBase):
    """startup information
    """

    optionList = [("servicestatus", "get a status of all running services", "slow", False)]
    def setup(self):
        self.addCopySpec("/etc/rc.d")
        
        self.collectExtOutput("/sbin/chkconfig --list", symlink = "chkconfig")
        if self.getOption('servicestatus'):
            self.collectExtOutput("/sbin/service --status-all")
        self.collectExtOutput("/sbin/runlevel")
        return

