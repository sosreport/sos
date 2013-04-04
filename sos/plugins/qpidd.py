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

    packages = ('qpidd', 'qpid-cpp-server', 'qpid-tools')

    def setup(self):
        """ performs data collection for mrg """
        self.add_cmd_output("/usr/bin/qpid-stat -e")
        self.add_cmd_output("/usr/bin/qpid-stat -b")
        self.add_cmd_output("/usr/bin/qpid-config")
        self.add_cmd_output("/usr/bin/qpid-config -b exchanges")
        self.add_cmd_output("/usr/bin/qpid-config -b queues")
        self.add_cmd_output("/usr/bin/qpid-stat -c")
        self.add_cmd_output("/usr/bin/qpid-route link list")
        self.add_cmd_output("/usr/bin/qpid-route route list")
        self.add_cmd_output("/bin/ls -lanR /var/lib/qpidd")

        self.add_copy_specs([
            "/etc/qpidd.conf",
            "/var/lib/qpid/syslog",
            "/etc/ais/openais.conf",
            "/var/log/cumin.log",
            "/var/log/mint.log"
            "/etc/sasl2/qpidd.conf",
            "/etc/qpid/qpidc.conf",
            "/etc/sesame/sesame.conf",
            "/etc/cumin/cumin.conf",
            "/etc/corosync/corosync.conf",
            "/var/lib/sesame",
            "/var/log/qpidd.log",
            "/var/log/sesame",
            "/var/log/cumin",
            "/var/log/cluster"])
