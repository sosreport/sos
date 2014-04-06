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

class Qpid(Plugin, RedHatPlugin):
    """Messaging related information
    """

    plugin_name = 'qpid'

    packages = ('qpidd', 'qpid-cpp-server', 'qpid-tools')

    def setup(self):
        """ performs data collection for mrg """
        self.add_cmd_outputs([
            "qpid-stat -e",
            "qpid-stat -b",
            "qpid-config",
            "qpid-config -b exchanges",
            "qpid-config -b queues",
            "qpid-stat -c",
            "qpid-route link list",
            "qpid-route route list",
            "ls -lanR /var/lib/qpidd"
        ])

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
            "/var/log/cluster"
        ])

# vim: et ts=4 sw=4
