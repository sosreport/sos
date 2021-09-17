# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin
import glob


class CephMGR(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH mgr'

    plugin_name = 'ceph_mgr'
    profiles = ('storage', 'virt', 'container')

    containers = ('ceph-mgr.*',)

    def check_enabled(self):
        return True if glob.glob('/var/lib/ceph/mgr/*/*') else False

    def setup(self):
        self.add_file_tags({
            '/var/log/ceph/ceph-mgr.*.log': 'ceph_mgr_log',
        })

        self.add_copy_spec([
            "/var/log/ceph/ceph-mgr*.log",
            "/var/lib/ceph/mgr/",
            "/var/lib/ceph/bootstrap-mgr/",
            "/run/ceph/ceph-mgr*",
        ])

        # more commands to be added later
        self.add_cmd_output([
            "ceph balancer status",
            "ceph mgr metadata",
        ])

        # more commands to be added later
        ceph_cmds = [
            "mgr module ls",
            "mgr dump",
        ]

        self.add_cmd_output([
            "ceph %s --format json-pretty" % s for s in ceph_cmds
        ], subdir="json_output", tags="insights_ceph_health_detail")

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
            "/etc/ceph/*bindpass*",
        ])

        # If containerized, run commands in containers
        containers_list = self.get_all_containers_by_regex("ceph-mgr*")
        if containers_list:
            for container in containers_list:
                self.add_cmd_output([
                    self.fmt_container_cmd(container[1], "ceph %s" % s)
                    for s in ceph_cmds
                ])
                break
        # Not containerized
        else:
            self.add_cmd_output([
                "ceph %s" % s for s in ceph_cmds
            ])

# vim: set et ts=4 sw=4 :
