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

class cobbler(sos.plugintools.PluginBase):
    """cobbler related information
    """
    def checkenabled(self):
        if self.isInstalled("cobbler"):
            return True
        return False

    def setup(self):
        self.addCopySpec("/etc/cobbler")
        self.addCopySpec("/var/log/cobbler")
        self.addCopySpec("/var/lib/rhn/kickstarts") 
        self.addCopySpec("/var/lib/cobbler")
        return
