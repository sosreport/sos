# Copyright (C) 2015 Red Hat, Inc. Neependra Khare <nkhare@redhat.com>
# Copyright (C) 2015 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin
import socket


class etcd(Plugin, RedHatPlugin):

    """etcd plugin
    """

    def port_report(self):
        """ Until etcd v2, the daemon listens on port 4001 for backward
        compatibility of v2.0 eariler. But etcd v3 no loger litens on 
        port 4001 and it listens on port 2379 only. 
        To collect information in any version, this plugin should check 
        which port is available.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect(("localhost", 2379))
        except socket.error, msg:
            self.sock.close()
            return "4001"
        self.sock.close()
        return "2379"

    def setup(self):
        self.add_copy_spec("/etc/etcd")

        curl_command = "curl -s http://localhost:" + str(self.port_report())
        self.add_cmd_output(str(curl_command) + "/version")
        self.add_cmd_output(str(curl_command) + "/v2/members")
        self.add_cmd_output(str(curl_command) + "/v2/stats/leader")
        self.add_cmd_output(str(curl_command) + "/v2/stats/self")
        self.add_cmd_output(str(curl_command) + "/v2/stats/store")
        self.add_cmd_output("ls -lR /var/lib/etcd/")


# vim: et ts=5 sw=4
