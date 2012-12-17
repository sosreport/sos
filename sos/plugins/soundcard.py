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

from sos.plugins import Plugin, RedHatPlugin
import os

class soundcard(Plugin, RedHatPlugin):
    """ Sound card information
    """

    def defaultenabled(self):
        return False

    def setup(self):
        self.addCopySpecs([
            "/proc/asound/*",
            "/etc/alsa/*",
            "/etc/asound.*"])
        self.addCmdOutput("/sbin/lspci | grep -i audio")
        self.addCmdOutput("/usr/bin/aplay -l")
        self.addCmdOutput("/usr/bin/aplay -L")
        self.addCmdOutput("/usr/bin/amixer")
        self.addCmdOutput("/sbin/lsmod | /bin/grep snd | /bin/awk '{print $1}'", suggest_filename = "sndmodules_loaded")
