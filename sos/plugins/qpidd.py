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
        if self.cInfo["policy"].pkgByName("qpidd") and \
        self.cInfo["policy"].pkgByName("python-qpid"):
            return True
        return False

    def setup(self):
        """ performs data collection for mrg """
        self.addCopySpec("/etc/qpidd.conf")
        self.collectExtOutput("/usr/bin/qpid-stat -q")
        self.collectExtOutput("/usr/bin/qpid-stat -e")
        self.collectExtOutput("/usr/bin/qpid-stat -b")
        self.addCopySpec("/var/lib/qpid/syslog")
        self.collectExtOutput("/usr/bin/qpid-config")
        self.collectExtOutput("/usr/bin/qpid-config -b exchanges")
        self.collectExtOutput("/usr/bin/qpid-config -b queues")
        self.collectExtOutput("/usr/bin/qpid-stat -c")
        self.collectExtOutput("/usr/bin/qpid-route link list")
        self.collectExtOutput("/usr/bin/qpid-route route list")
        self.addCopySpec("/etc/ais/openais.conf")
        self.collectExtOutput("ls -lR /var/lib/qpidd")
        self.addCopySpec("/var/log/cumin.log")
        self.addCopySpec("/var/log/mint.log")
