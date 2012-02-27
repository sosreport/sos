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

from sos.plugins import Plugin, RedHatPlugin

class qpidd(Plugin, RedHatPlugin):
    """Messaging related information
    """

    packages = ('qpidd', 'python-qpid')

    def setup(self):
        """ performs data collection for mrg """
        self.collectExtOutput("/usr/bin/qpid-stat -q")
        self.collectExtOutput("/usr/bin/qpid-stat -e")
        self.collectExtOutput("/usr/bin/qpid-stat -b")
        self.collectExtOutput("/usr/bin/qpid-config")
        self.collectExtOutput("/usr/bin/qpid-config -b exchanges")
        self.collectExtOutput("/usr/bin/qpid-config -b queues")
        self.collectExtOutput("/usr/bin/qpid-stat -c")
        self.collectExtOutput("/usr/bin/qpid-route link list")
        self.collectExtOutput("/usr/bin/qpid-route route list")
        self.collectExtOutput("/bin/ls -lanR /var/lib/qpidd")
        self.addCopySpecs([
            "/etc/qpidd.conf",
            "/var/lib/qpid/syslog",
            "/etc/ais/openais.conf",
            "/var/log/cumin.log",
            "/var/log/mint.log"])
