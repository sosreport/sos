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

class memory(sos.plugintools.PluginBase):
    """memory usage information
    """
    def setup(self):
        self.addCopySpec("/proc/pci")
        self.addCopySpec("/proc/meminfo")
        self.addCopySpec("/proc/vmstat")
        self.addCopySpec("/proc/slabinfo")
        self.addCopySpec("/proc/pagetypeinfo")
        
        self.collectExtOutput("/bin/dmesg | grep -e 'e820.' -e 'aperature.'")
        self.collectExtOutput("/usr/bin/free", symlink = "free")
        self.collectExtOutput("/usr/bin/free -m")
        return

