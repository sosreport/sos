# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin


class Qpid(Plugin, RedHatPlugin):
    """Messaging related information
    """

    plugin_name = 'qpid'

    packages = ('qpidd', 'qpid-cpp-server', 'qpid-tools')

    def setup(self):
        """ performs data collection for qpid broker """
        self.add_cmd_outputs([
            "qpid-stat -g",  # applies since 0.18 version
            "qpid-stat -b",  # applies to pre-0.18 versions
            "qpid-stat -c",
            "qpid-stat -e",
            "qpid-stat -q",
            "qpid-stat -u",
            "qpid-stat -m",  # applies since 0.18 version
            "qpid-config exchanges"
            "qpid-config queues"
            "qpid-config exchanges -b",  # applies to pre-0.18 versions
            "qpid-config queues -b",  # applies to pre-0.18 versions
            "qpid-config exchanges -r",  # applies since 0.18 version
            "qpid-config queues -r",  # applies since 0.18 version
            "qpid-route link list",
            "qpid-route route list",
            "qpid-cluster",  # applies to pre-0.22 versions
            "qpid-ha query",  # applies since 0.22 version
            "ls -lanR /var/lib/qpidd"
        ])

        self.add_copy_specs([
            "/etc/qpidd.conf",  # applies to pre-0.22 versions
            "/etc/qpid/qpidd.conf",  # applies since 0.22 version
            "/var/lib/qpid/syslog",
            "/etc/ais/openais.conf",
            "/var/log/cumin.log",
            "/var/log/mint.log",
            "/etc/sasl2/qpidd.conf",
            "/etc/qpid/qpidc.conf",
            "/etc/sesame/sesame.conf",
            "/etc/cumin/cumin.conf",
            "/etc/corosync/corosync.conf",
            "/var/lib/sesame",
            "/var/log/qpidd.log",
            "/var/log/sesame",
            "/var/log/cumin"
        ])

# vim: et ts=4 sw=4
