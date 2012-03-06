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

class lsbrelease(sos.plugintools.PluginBase):
    """Linux Standard Base information
    """
    def diagnose(self):
        if not os.path.exists("/etc/redhat-release"):
            self.addDiagnose("/etc/redhat-release missing")
            return
    def setup(self):
        self.collectExtOutput("/usr/bin/lsb_release -a")
        self.collectExtOutput("/usr/bin/lsb_release -d", suggest_filename = "lsb_release", symlink = "lsb-release")
        self.addCopySpec("/etc/lsb-release*")
        return    
