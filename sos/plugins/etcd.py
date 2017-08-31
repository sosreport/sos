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

    plugin_name = 'etcd'
    packages = ('etcd',)
    profiles = ('system', 'services', 'cluster')

    cmd = 'etcdctl'

    def setup(self):
        etcd_url = self.get_etcd_url()

        self.add_copy_spec('/etc/etcd')

        subcmds = [
           '--version',
           'member list',
           'cluster-health',
           'ls --recursive',
        ]

        self.add_cmd_output(['%s %s' % (self.cmd, sub) for sub in subcmd])

        urls = [
            '/v2/stats/leader',
            '/v2/stats/self',
            '/v2/stats/store',
        ]

        if etcd_url:
            self.add_cmd_output(['curl -s %s%s' % (etcd_url, u) for u in urls])

        self.add_cmd_output("ls -lR /var/lib/etcd/")

    def get_etcd_url(self):
        try:
            with open('/etc/etcd/etcd.conf', 'r') as ef:
                for line in ef:
                    if line.startswith('ETCD_LISTEN_CLIENT_URLS'):
                        return line.split('=')[1].replace('"', '').strip()
        # If we can't read etcd.conf, assume defaults by etcd version
        except:
            ver = self.policy().package_manager.get_pkg_list()['etcd']
            ver = ver['version'][0]
            if ver == '2':
                return 'http://localhost:4001'
            if ver == '3':
                return 'http://localhost:2379'

# vim: et ts=5 sw=4
