# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin
from socket import gethostname


class Ceph(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH distributed storage'

    plugin_name = 'ceph'
    profiles = ('storage', 'virt')
    ceph_hostname = gethostname()

    packages = (
        'ceph',
        'ceph-mds',
        'ceph-common',
        'libcephfs1',
        'ceph-fs-common',
        'calamari-server',
        'librados2'
    )

    services = (
        'ceph-nfs@pacemaker',
        'ceph-mds@%s' % ceph_hostname,
        'ceph-mon@%s' % ceph_hostname,
        'ceph-mgr@%s' % ceph_hostname,
        'ceph-radosgw@*',
        'ceph-osd@*'
    )

    def setup(self):
        all_logs = self.get_option("all_logs")

        self.add_file_tags({
            '.*/ceph.conf': 'ceph_conf',
            '/var/log/ceph/ceph.log.*': 'ceph_log',
            '/var/log/ceph/ceph-osd.*.log': 'ceph_osd_log'
        })

        if not all_logs:
            self.add_copy_spec([
                "/var/log/ceph/*.log",
                "/var/log/radosgw/*.log",
                "/var/log/calamari/*.log"
            ])
        else:
            self.add_copy_spec([
                "/var/log/ceph/",
                "/var/log/calamari",
                "/var/log/radosgw"
            ])

        self.add_copy_spec([
            "/etc/ceph/",
            "/etc/calamari/",
            "/var/lib/ceph/",
            "/run/ceph/"
        ])

        self.add_cmd_output([
            "ceph mon stat",
            "ceph mon_status",
            "ceph quorum_status",
            "ceph mgr module ls",
            "ceph mgr metadata",
            "ceph balancer status",
            "ceph osd metadata",
            "ceph osd erasure-code-profile ls",
            "ceph report",
            "ceph osd crush show-tunables",
            "ceph-disk list",
            "ceph versions",
            "ceph features",
            "ceph insights",
            "ceph osd crush dump",
            "ceph -v",
            "ceph-volume lvm list",
            "ceph crash stat",
            "ceph crash ls",
            "ceph config log",
            "ceph config generate-minimal-conf",
            "ceph config-key dump",
        ])

        ceph_cmds = [
            "status",
            "health detail",
            "osd tree",
            "osd stat",
            "osd df tree",
            "osd dump",
            "osd df",
            "osd perf",
            "osd blocked-by",
            "osd pool ls detail",
            "osd pool autoscale-status",
            "osd numa-status",
            "device ls",
            "mon dump",
            "mgr dump",
            "mds stat",
            "df",
            "df detail",
            "fs ls",
            "fs dump",
            "pg dump",
            "pg stat",
            "time-sync-status",
        ]

        self.add_cmd_output([
            "ceph %s" % s for s in ceph_cmds
        ])

        self.add_cmd_output([
            "ceph %s --format json-pretty" % s for s in ceph_cmds
        ], subdir="json_output", tags="insights_ceph_health_detail")

        for service in self.services:
            self.add_journal(units=service)

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

# vim: set et ts=4 sw=4 :
