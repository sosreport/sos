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

class cluster(sos.plugintools.PluginBase):
    """cluster related information
    """
    def setup(self):
        self.collectExtOutput("/sbin/fdisk -l")
        self.addCopySpec("/etc/cluster.conf")
        self.addCopySpec("/etc/cluster.xml")
        self.addCopySpec("/etc/cluster")
        self.collectExtOutput("/usr/sbin/rg_test test /etc/cluster/cluster.conf")
        self.addCopySpec("/proc/cluster")
        self.collectExtOutput("/usr/bin/cman_tool status")
        self.collectExtOutput("/usr/bin/cman_tool services")
        self.collectExtOutput("/usr/bin/cman_tool -af nodes")
        self.collectExtOutput("/usr/bin/ccs_tool lsnode")
        self.collectExtOutput("/usr/bin/openais-cfgtool -s")
        self.collectExtOutput("/usr/bin/clustat")
        return

    def postproc(self):
        self.doRegexSub("/etc/cluster/cluster.conf", r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")", r"\1***")
        return
