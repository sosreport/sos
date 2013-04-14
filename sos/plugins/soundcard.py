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

class soundcard(Plugin, RedHatPlugin):
    """ Sound card information
    """

    def default_enabled(self):
        return False

    def setup(self):
        self.add_copy_specs([
            "/proc/asound/*",
            "/etc/alsa/*",
            "/etc/asound.*"])
        self.add_cmd_output("lspci | grep -i audio")
        self.add_cmd_output("aplay -l")
        self.add_cmd_output("aplay -L")
        self.add_cmd_output("amixer")
        self.add_cmd_output("lsmod | grep snd | awk '{print $1}'", suggest_filename = "sndmodules_loaded")
