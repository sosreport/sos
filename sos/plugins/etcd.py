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


class etcd(Plugin, RedHatPlugin):

    """etcd plugin
    """

    def report_url_and_port(self):
        access_url_port = 'http://localhost:4001'
        peer_flag = False
        f = open('/etc/etcd/etcd.conf', 'r')

        for line in f:
            if line.startswith('ETCD_LISTEN_CLIENT_URLS='):
                access_url_port = line[len('ETCD_LISTEN_CLIENT_URLS='):-1]
            elif line.startswith('[peer]'):
                peer_flag = True
            elif line.startswith('addr =') and (peer_flag is False):
                access_url_port = line[len('addr ='):-1]

        f.close()
        return access_url_port

    def setup(self):
        self.add_copy_spec("/etc/etcd")

        curl_command = "curl -s {}".format(self.report_url_and_port())
        self.add_cmd_output("{}/version".format(curl_command))
        self.add_cmd_output("{}/v2/members".format(curl_command))
        self.add_cmd_output("{}/v2/stats/leader".format(curl_command))
        self.add_cmd_output("{}/v2/stats/self".format(curl_command))
        self.add_cmd_output("{}/v2/stats/store".format(curl_command))
        self.add_cmd_output("ls -lR /var/lib/etcd/")

# vim: et ts=5 sw=4
