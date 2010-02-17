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

class soundcard(sos.plugintools.PluginBase):
    """ Sound card information
    """

    def defaultenabled(self):
        return False

    def setup(self):
        self.addCopySpec("/proc/asound/*")
        self.addCopySpec("/etc/alsa/*")
        self.addCopySpec("/etc/asound.*")
        self.collectExtOutput("/sbin/lspci | grep -i audio")
        self.collectExtOutput("/usr/bin/aplay -l")
        self.collectExtOutput("/usr/bin/aplay -L")
        self.collectExtOutput("/usr/bin/amixer")
        self.collectExtOutput("/sbin/lsmod | /bin/grep snd | /bin/awk '{print $1}'", suggest_filename = "sndmodules_loaded")
        return 
