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

class x11(sos.plugintools.PluginBase):
    """X related information
    """
    def checkenabled(self):
        try:os.stat("/etc/X11")
        except:pass
        else:return True
        return False

    def setup(self):
        self.addCopySpec("/etc/X11")
        self.addCopySpec("/var/log/Xorg.*.log")
        self.addCopySpec("/var/log/XFree86.*.log")
        self.collectExtOutput("/bin/dmesg | grep -e 'agpgart.'")

        self.addForbiddenPath("/etc/X11/X")
        self.addForbiddenPath("/etc/X11/fontpath.d")
        
        # TODO: if there is a need for kde that can be added here as well
        if os.path.exists("/etc/gdm"):
            self.addCopySpec("/etc/gdm")

        return

