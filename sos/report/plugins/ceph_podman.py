# Copyright (C) 2020 Meiyan Zheng <mzheng@redhat.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin
from socket import gethostname
import re


class CephPodman(Plugin, RedHatPlugin):
    short_desc = 'Containerized Ceph distributed storage'
    plugin_name = 'ceph_podman'
    profiles = ('storage', 'container')
    ceph_hostname = gethostname()
    files = (
        '/etc/ceph/ceph.conf',
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
        self._container_mon_name = self.get_container_by_name('ceph-mon-*')
        self._container_osd_name = self.get_container_by_name('ceph-osd-*')
        self.run_cmd = "podman exec"

        if self._container_mon_name:
            cmds = [
                'ceph mon stat',
                'ceph mon_status',
                'ceph quorum_status',
                'ceph mgr module ls',
                'ceph mgr metadata',
                'ceph osd metadata',
                'ceph osd erasure-code-profile ls',
                'ceph report',
                'ceph osd crush show-tunables',
                'ceph versions',
                'ceph features',
                'ceph osd crush dump',
                'ceph -v',
                'ceph crash stat',
                'ceph crash ls',
                'ceph config log',
                'ceph config generate-minimal-conf',
                'ceph config-key dump',
                'ceph status',
                'ceph health detail',
                'ceph osd tree',
                "ceph osd stat",
                "ceph osd df tree",
                "ceph osd dump",
                "ceph osd df",
                "ceph osd perf",
                "ceph osd blocked-by",
                "ceph osd pool ls detail",
                "ceph osd numa-status",
                "ceph device ls",
                "ceph mon dump",
                "ceph mgr dump",
                "ceph mds stat",
                "ceph df",
                "ceph df detail",
                "ceph fs ls",
                "ceph fs dump",
                "ceph pg dump",
                "ceph pg stat",
            ]
            container_cmds = [
                self.fmt_container_cmd(self._container_mon_name,
                                       cmd) for cmd in cmds
            ]
            self.add_cmd_output(container_cmds, foreground=True)

        if self._container_osd_name:
            cmds = [
                'ceph -v',
                'ceph-volume lvm list',
            ]
            osd_containers = self.get_all_containers_by_name('ceph-osd-*')
            for c in osd_containers:
                container_cmds = [
                    self.fmt_container_cmd(c[1], cmd) for cmd in cmds
                ]
                self.add_cmd_output(container_cmds, foreground=True)

        self.add_copy_spec([
            "/etc/ceph/",
            "/var/lib/ceph/",
            "/run/ceph/"
        ])

        for service in self.services:
            self.add_journal(units=service)

        self.add_forbidden_path([
            "/etc/ceph/*keyring*",
            "/var/lib/ceph/*keyring*",
            "/var/lib/ceph/*/*keyring*",
            "/var/lib/ceph/*/*/*keyring*",
            "/var/lib/ceph/osd",
            "/var/lib/ceph/mon",
            "/var/lib/ceph/tmp/*mnt*",
            "/etc/ceph/*bindpass*"
        ])

    def fmt_container_cmd(self, container, cmd):
        return "%s %s %s" % (self.run_cmd, container, cmd)

    def get_all_containers_by_name(self, name):
        return [c for c in self.get_containers() if re.match(name, c[1])]
