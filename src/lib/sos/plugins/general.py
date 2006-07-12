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

class general(sos.plugintools.PluginBase):
    """This plugin gathers very basic system information
    """
    def collect(self):
        self.copyFileOrDir("/etc/redhat-release")
        self.copyFileOrDir("/etc/sysconfig")
        self.copyFileOrDir("/proc/stat")
        self.copyFileOrDir("/var/log/dmesg")
        self.copyFileOrDir("/var/log/messages")
        self.copyFileOrDir("/var/log/sa")
        self.copyFileOrDir("/var/log/secure")
        self.copyFileOrDir("/var/log/up2date")
        self.copyFileOrDir("/etc/exports")        
        self.copyFileGlob("/etc/cups/*.conf")
        self.runExe("/bin/hostname")
        self.runExe("/bin/date")
        self.runExe("/usr/bin/uptime")
        return

