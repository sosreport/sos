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
from os.path import exists

class postfix(sos.plugintools.PluginBase):
    """mail server related information
    """
    def checkenabled(self):
        if self.isInstalled("postfix") or exists("/etc/rc.d/init.d/postfix"):
            return True
        return False
        
    def setup(self):
        self.addCopySpec("/etc/mail")
        self.addCopySpec("/etc/postfix/main.cf")
        self.addCopySpec("/etc/postfix/master.cf")
        self.collectExtOutput("/usr/sbin/postconf")
        return

