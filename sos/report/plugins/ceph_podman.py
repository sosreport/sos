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
import re

class CephPodman(Plugin, RedHatPlugin):
    short_desc = 'Containerized Ceph distributed storage'
    plugin_name = 'ceph_podman'
    profiles = ('storage', 'container')
    packages = ('podman',)

    def setup(self):
        self._container_mon_name = self.get_container_by_name('ceph-mon-*')
        self._container_osd_name = self.get_container_by_name('ceph-osd-*')

        self.add_copy_spec([
            "/etc/ceph/",
            "/var/lib/ceph/",
            "/run/ceph/"
        ])

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
            container_cmds = self.cmd_convert_to_container(cmds, self._container_mon_name)
            self.add_cmd_output(container_cmds, foreground=True)

        if self._container_osd_name:
            cmds = [
                'ceph -v',
                'ceph-volume lvm list',
            ]
            osd_containers = self.get_all_containers_by_name('ceph-osd-*')
            for c in osd_containers:
                container_cmds = self.cmd_convert_to_container(cmds, c)
                self.add_cmd_output(container_cmds, foreground=True)

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

    def cmd_convert_to_container(self, cmds, container_name):
        container_cmds = []
        for cmd in cmds:
            container_cmds.append('podman exec %s %s' % (container_name, cmd))
        return container_cmds

    def get_all_containers_by_name(self, name):
        all_containers = self.get_containers(get_all=True)
        containers_by_name = []
        for c in all_containers:
            if re.match(name,c[1]):
                containers_by_name.append(c[1])
        return containers_by_name
