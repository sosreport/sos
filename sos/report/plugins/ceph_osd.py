# Copyright (C) 2023 Canonical Ltd., Nikhil Kshirsagar <nkshirsagar@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class CephOSD(Plugin, RedHatPlugin, UbuntuPlugin):
    """
    This plugin is for capturing information from Ceph OSD nodes. While the
    majority of this plugin should be version agnostic, several collections are
    dependent upon the version of Ceph installed. Versions that correlate to
    RHCS 4 or RHCS 5 are explicitly handled for differences such as those
    pertaining to log locations on the host filesystem.

    Note that while this plugin will activate based on the presence of Ceph
    containers, commands are run directly on the host as those containers are
    often not configured to successfully run the `ceph` commands collected by
    this plugin. These commands are majorly `ceph daemon` commands that will
    reference discovered admin sockets under /var/run/ceph.
    """

    short_desc = 'CEPH osd'

    plugin_name = 'ceph_osd'
    profiles = ('storage', 'virt', 'container', 'ceph')
    containers = ('ceph-(.*-)?osd.*',)
    files = ('/var/lib/ceph/osd/*', '/var/lib/ceph/*/osd*',
             '/var/snap/microceph/common/data/osd/*')

    def setup(self):
        all_logs = self.get_option("all_logs")
        directory = ''
        microceph_pkg = self.policy.package_manager.pkg_by_name('microceph')
        cmds = [
            # will work pre quincy
            "bluestore bluefs available",
            "dump_reservations",
            # will work quincy onward
            "bluefs stats",
            "bluestore bluefs device info",
            "config diff",
            "config show",
            "counter dump",
            "counter schema",
            "dump_blocked_ops",
            "dump_blocklist",
            "dump_historic_ops_by_duration",
            "dump_historic_slow_ops",
            "dump_mempools",
            "dump_op_pq_state",
            "dump_ops_in_flight",
            "dump_osd_network",
            "dump_pgstate_history",
            "dump_recovery_reservations",
            "dump_scrubs",
            "dump_watchers",
            "get_mapped_pools",
            "list_devices",
            "list_unfound",
            "log dump",
            "objecter_requests",
            "ops",
            "perf dump",
            "perf histogram dump",
            "perf schema",
            "status",
            "version",
        ]

        if not microceph_pkg:
            directory = '/var/run/ceph'
            self.add_file_tags({
                "/var/log/ceph/(.*/)?ceph-(.*-)?osd.*.log": 'ceph_osd_log',
            })

            self.add_forbidden_path([
                "/etc/ceph/*keyring*",
                "/var/lib/ceph/**/*keyring*",
                # Excludes temporary ceph-osd mount location like
                # /var/lib/ceph/tmp/mnt.XXXX from sos collection.
                "/var/lib/ceph/**/tmp/*mnt*",
                "/etc/ceph/*bindpass*"
            ])

            # Only collect OSD specific files
            self.add_copy_spec([
                "/run/ceph/**/ceph-osd*",
                "/var/lib/ceph/**/kv_backend",
                "/var/log/ceph/**/ceph-osd*.log",
                "/var/log/ceph/**/ceph-volume*.log",
            ])

            self.add_cmd_output([
                "ceph-disk list",
                "ceph-volume lvm list"
            ])

            if all_logs:
                self.add_copy_spec([
                    "/var/log/ceph/**/ceph-osd*.log*",
                    "/var/log/ceph/**/ceph-volume*.log*",
                ])

        else:
            directory = '/var/snap/microceph/current/run'
            # Only collect microceph files, don't run any commands
            self.add_forbidden_path([
                "/var/snap/microceph/common/**/*keyring*",
                "/var/snap/microceph/current/**/*keyring*",
                "/var/snap/microceph/common/state/*",
            ])

            self.add_copy_spec([
                "/var/snap/microceph/common/data/osd/*",
                "/var/snap/microceph/common/logs/*ceph-osd*.log",
            ])

            if all_logs:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/*ceph-osd*.log*",
                ])

        # common add_cmd_output for ceph and microceph
        self.add_cmd_output([
            f"ceph daemon {i} {c}" for i in
            self.get_socks(directory) for c in cmds]
        )

    def get_socks(self, directory):
        """
        Find any available admin sockets under /var/run/ceph (or subdirs for
        later versions of Ceph) which can be used for ceph daemon commands
        """
        ceph_sockets = []
        for rdir, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.asok') and 'osd' in file:
                    ceph_sockets.append(self.path_join(rdir, file))
        return ceph_sockets

# vim: set et ts=4 sw=4 :
