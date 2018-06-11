# Copyright (C) 2015 Red Hat, Inc. Neependra Khare <nkhare@redhat.com>
# Copyright (C) 2015 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class etcd(Plugin, RedHatPlugin):
    """etcd plugin
    """

    plugin_name = 'etcd'
    packages = ('etcd',)
    profiles = ('container', 'system', 'services', 'cluster')

    cmd = 'etcdctl'

    def setup(self):
        etcd_url = self.get_etcd_url()

        self.add_forbidden_path('/etc/etcd/ca')
        self.add_copy_spec('/etc/etcd')

        subcmds = [
           '--version',
           'member list',
           'cluster-health',
           'ls --recursive',
        ]

        self.add_cmd_output(['%s %s' % (self.cmd, sub) for sub in subcmds])

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
        except IOError:
            # assume v3 is the default
            url = 'http://localhost:2379'
            try:
                ver = self.policy.package_manager.get_pkg_list()['etcd']
                ver = ver['version'][0]
                if ver == '2':
                    url = 'http://localhost:4001'
            except Exception:
                # fallback when etcd is not installed
                pass
            return url

# vim: et ts=5 sw=4
