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
    def setup(self):
        self.addCopySpec("/etc/redhat-release")
        self.addCopySpec("/etc/sysconfig")
        self.addCopySpec("/proc/stat")
        self.addCopySpec("/var/log/dmesg")
        self.addCopySpec("/var/log/messages")
        self.addCopySpec("/var/log/sa")
        self.addCopySpec("/var/log/secure")
        self.addCopySpec("/var/log/up2date")
        self.addCopySpec("/etc/exports")        
        self.collectExtOutput("/bin/hostname", root_symlink = "hostname")
        self.collectExtOutput("/bin/date", root_symlink = "date")
        self.collectExtOutput("/usr/bin/uptime", root_symlink = "uptime")
        return

    def postproc(self):
        self.doRegexSub("/etc/sysconfig/rhn/up2date", r"(\s*proxyPassword\s*=\s*)\S+", r"\1***")
        return
