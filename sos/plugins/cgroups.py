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

class cgroups(sos.plugintools.PluginBase):
    """cgroup subsystem information
    """

    def setup(self):
        self.addCopySpec("/proc/cgroups")
        self.addCopySpec("/etc/sysconfig/cgconfig")
        self.addCopySpec("/etc/sysconfig/cgred.conf")
        self.addCopySpec("/etc/cgsnapshot_blacklist.conf")
        self.addCopySpec("/etc/cgconfig.conf")
        self.addCopySpec("/etc/cgrules.conf")
        return
