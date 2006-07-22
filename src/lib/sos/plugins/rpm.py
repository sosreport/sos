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

class rpm(sos.plugintools.PluginBase):
    """This plugin gathers RPM information
    """
    optionList = [("rpmq", "Queries for package information via rpm -q", "fast", 1),
                  ("rpmva", "Runs a verify on all packages", "slow", 0)]
                  
    def setup(self):
        self.addCopySpec("/var/log/rpmpkgs")
        
        if self.isOptionEnabled("rpmq"):
          self.collectExtOutput("/bin/rpm -qa --qf \"%{NAME}-%{VERSION}-%{RELEASE}-%{ARCH}\n\"")
      
        if self.isOptionEnabled("rpmva"):
          self.collectExtOutput("/bin/rpm -Va")
        return

