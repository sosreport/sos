# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class CephMDS(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH mds'
    plugin_name = 'ceph_mds'
    profiles = ('storage', 'virt', 'container', 'ceph')
    containers = ('ceph-(.*-)?fs.*',)
    files = ('/var/lib/ceph/mds/*', '/var/lib/ceph/*/mds.*',
             '/var/snap/microceph/common/data/mds/*')

    def setup(self):
        all_logs = self.get_option("all_logs")
        microceph = self.policy.package_manager.pkg_by_name('microceph')
        if microceph:
            if all_logs:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/*ceph-mds*.log*",
                ])
            else:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/*ceph-mds*.log",
                ])
            self.add_forbidden_path([
                "/var/snap/microceph/common/**/*keyring*",
                "/var/snap/microceph/current/**/*keyring*",
                "/var/snap/microceph/common/state/*",
            ])
        else:
            self.add_file_tags({
                '/var/log/ceph/ceph-mds.*.log': 'ceph_mds_log',
            })

            if not all_logs:
                self.add_copy_spec(["/var/log/ceph/ceph-mds*.log",])
            else:
                self.add_copy_spec(["/var/log/ceph/ceph-mds*.log*",])

            self.add_copy_spec([
                "/var/lib/ceph/bootstrap-mds/",
                "/var/lib/ceph/mds/",
                "/var/lib/ceph/*/mds.*",
                "/run/ceph/ceph-mds*",
            ])

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

        cmds = [
            "cache status",
            "client ls",
            "config diff",
            "config show",
            "counter dump",
            "counter schema",
            "damage ls",
            "dump loads",
            "dump tree",
            "dump_blocked_ops",
            "dump_historic_ops",
            "dump_historic_ops_by_duration",
            "dump_mempools",
            "dump_ops_in_flight",
            "get subtrees",
            "objecter_requests",
            "ops",
            "perf dump",
            "perf histogram dump",
            "perf histogram schema",
            "perf schema",
            "session ls",
            "status",
            "version",
        ]

        # If containerized, run commands in containers
        try:
            cname = self.get_all_containers_by_regex("ceph-mds*")[0][1]
        except Exception:  # pylint: disable=broad-except
            cname = None

        directory = '/var/snap/microceph/current/run' if microceph \
            else '/var/run/ceph'

        # common add_cmd_output for ceph and microceph
        self.add_cmd_output([
            f"ceph daemon {i} {c}" for i in
            self.get_socks(directory) for c in cmds],
             container=cname
        )

    def get_socks(self, directory):
        """
        Find any available admin sockets under /var/run/ceph (or subdirs for
        later versions of Ceph) which can be used for ceph daemon commands
        """
        ceph_sockets = []
        for rdir, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.asok') and 'mds' in file:
                    ceph_sockets.append(self.path_join(rdir, file))
        return ceph_sockets


# vim: set et ts=4 sw=4 :
