## This program is free software; you can redistribute it and/or modify
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

class qpidd(sos.plugintools.PluginBase):
    """Messaging related information
    """
    def checkenabled(self):
        """ checks if mrg enabled """
        if self.cInfo["policy"].pkgByName("qpid-cpp-server") and \
        self.cInfo["policy"].pkgByName("qpid-tools"):
            return True
        return False

    def setup(self):
        """ performs data collection for mrg """
        self.addCopySpec("/etc/qpidd.conf")
        self.addCopySpec("/etc/sasl2/qpidd.conf")
        self.addCopySpec("/etc/qpid/qpidc.conf")
        self.addCopySpec("/etc/sesame/sesame.conf")
        self.addCopySpec("/etc/cumin/cumin.conf")
        self.addCopySpec("/etc/corosync/corosync.conf")
        self.addCopySpec("/var/lib/sesame")
        self.addCopySpec("/var/log/qpidd.log")
        self.addCopySpec("/var/log/sesame")
        self.addCopySpec("/var/log/cumin")
        self.addCopySpec("/var/log/cluster")
        
        self.collectExtOutput("/usr/bin/qpid-config queues")
        self.collectExtOutput("/usr/bin/qpid-config exchanges")
        self.collectExtOutput("/usr/bin/qpid-config exchanges -b")
        self.collectExtOutput("/usr/bin/qpid-stat -b")
        self.collectExtOutput("/usr/bin/qpid-stat -e")
        self.collectExtOutput("/usr/bin/qpid-stat -q")
        self.collectExtOutput("/usr/bin/qpid-stat -u")
        self.collectExtOutput("/usr/bin/qpid-stat -c")
        self.collectExtOutput("/usr/bin/qpid-route route list")
        self.collectExtOutput("/usr/bin/qpid-route link list")
        self.collectExtOutput("/usr/bin/qpid-cluster")
        self.collectExtOutput("/usr/bin/qpid-cluster -c")
        self.collectExtOutput("ls -lR /var/lib/qpidd")
        self.collectExtOutput("ls -lR /opt/rh-qpid")
