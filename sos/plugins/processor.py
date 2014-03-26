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

class Processor(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """CPU information
    """

    plugin_name = 'processor'

    def setup(self):
        self.add_copy_specs([
            "/proc/cpuinfo",
            "/sys/class/cpuid",
            "/sys/devices/system/cpu"
        ])
        
        if self.policy().pkg_by_name("cpufreq-utils"):
            self.add_cmd_output("cpufreq-info")
            self.add_cmd_output("cpupower info")
            self.add_cmd_output("cpupower frequency-info")

        if self.policy().pkg_by_name("kernel-tools"):
            self.add_cmd_output("cpupower info")
            self.add_cmd_output("cpupower frequency-info")
            self.add_cmd_output("cpupower idle-info")

        if self.policy().get_arch().endswith("386"):
            self.add_cmd_output("x86info -a")

        self.add_cmd_output("lscpu")



# vim: et ts=4 sw=4
