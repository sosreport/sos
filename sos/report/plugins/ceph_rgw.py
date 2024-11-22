# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json

from socket import gethostname
from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class CephRGW(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH rgw'

    plugin_name = 'ceph_rgw'
    profiles = ('storage', 'virt', 'container', 'webserver', 'ceph')
    containers = ('ceph-(.*)?rgw.*',)
    files = ('/var/lib/ceph/radosgw/*',
             '/var/snap/microceph/common/data/radosgw/*')

    def setup(self):
        all_logs = self.get_option("all_logs")
        cmds = ['bucket limit check',
                'bucket list',
                'bucket stats',
                'datalog list',
                'datalog status',
                'gc list',
                'lc list',
                'log list',
                'metadata sync status',
                'period list',
                'realm list',
                'reshard list',
                'sync error list',
                'sync status',
                'zone list',
                'zone placement list',
                'zonegroup list',
                'zonegroup placement list',
                ]

        microceph = self.policy.package_manager.pkg_by_name('microceph')
        if microceph:
            if all_logs:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/*ceph-radosgw*.log*",
                ])
            else:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/*ceph-radosgw*.log",
                ])
            self.add_forbidden_path([
                "/var/snap/microceph/common/**/*keyring*",
                "/var/snap/microceph/current/**/*keyring*",
                "/var/snap/microceph/common/state/*",
            ])
        else:
            if not all_logs:
                self.add_copy_spec('/var/log/ceph/ceph-client.rgw*.log',
                                   tags='ceph_rgw_log')
            else:
                self.add_copy_spec('/var/log/ceph/ceph-client.rgw*.log*',
                                   tags='ceph_rgw_log')

            self.add_forbidden_path([
                "/etc/ceph/*keyring*",
                "/var/lib/ceph/*keyring*",
                "/var/lib/ceph/*/*keyring*",
                "/var/lib/ceph/*/*/*keyring*",
                "/var/lib/ceph/osd",
                "/var/lib/ceph/mon",
                # Excludes temporary ceph-osd mount location like
                # /var/lib/ceph/tmp/mnt.XXXX from sos collection.
                "/var/lib/ceph/tmp/*mnt*",
                "/etc/ceph/*bindpass*"
            ])

        # Get commands output for both Ceph and microCeph
        rgw_id = "radosgw.gateway" if microceph else "rgw." + gethostname()
        self.add_cmd_output([f"radosgw-admin --id={rgw_id} {c}" for c in cmds])

        # Get all the zone data
        res = self.collect_cmd_output(f'radosgw-admin --id={rgw_id} zone list')
        if res['status'] == 0:
            try:
                _out = json.loads(res['output'])
                zone_list = _out['zones']
                for zone in zone_list:
                    self.add_cmd_output(f'radosgw-admin --id={rgw_id} '
                                        f'zone get --rgw-zone={zone}')
            except ValueError as err:
                self._log_error(f'Error while getting get rgw '
                                f'zone list: {err}')

        # Get all the zonegroup data
        res = self.collect_cmd_output(f'radosgw-admin --id={rgw_id} '
                                      f'zonegroup list')
        if res['status'] == 0:
            try:
                _out = json.loads(res['output'])
                zonegroups = _out['zonegroups']
                for zgroup in zonegroups:
                    self.add_cmd_output(f'radosgw-admin --id={rgw_id} '
                                        f'zone get --rgw-zonegroup={zgroup}')
            except ValueError as err:
                self._log_error(f'Error while getting get rgw '
                                f'zonegroup list: {err}')

    def postproc(self):
        """ Obfuscate secondary zone access keys """

        rsub = r'("access_key":|"secret_key":)\s.*'
        self.do_cmd_output_sub("radosgw-admin", rsub, r'\1 "**********"')


# vim: set et ts=4 sw=4 :
