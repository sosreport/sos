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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
from glob import glob
import os

class Hardware(Plugin):
    """hardware related information
    """

    plugin_name = "hardware"

    def setup(self):
        self.add_copy_specs([
            "/proc/interrupts",
            "/proc/irq",
            "/proc/dma",
            "/proc/devices",
            "/proc/rtc",
            "/var/log/mcelog"
        ])

        self.add_cmd_output("dmidecode", root_symlink = "dmidecode")
        

class RedHatHardware(Hardware, RedHatPlugin):
    """hardware related information for Red Hat distribution
    """

    def setup(self):
        super(RedHatHardware, self).setup()
        hwpaths = glob("/usr/share/rhn/up2date*client/hardware.py")
        if (len(hwpaths) == 0):
            return
        self.add_cmd_output("python " + hwpaths[0])


class DebianHardware(Hardware, DebianPlugin, UbuntuPlugin):
    """hardware related information for Debian distribution
    """

    def setup(self):
        super(DebianHardware, self).setup()
