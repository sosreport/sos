# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin
import glob


class CephOSD(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH osd'

    plugin_name = 'ceph_osd'
    profiles = ('storage', 'virt', 'container')
    containers = ('ceph-osd.*',)

    def check_enabled(self):
        return True if glob.glob('/var/lib/ceph/osd/*/*') else False

    def setup(self):
        self.add_file_tags({
            '/var/log/ceph/ceph-osd.*.log': 'ceph_osd_log',
        })

        # Only collect OSD specific files
        self.add_copy_spec([
            "/run/ceph/ceph-osd*",
            "/var/lib/ceph/osd/*/kv_backend",
            "/var/log/ceph/ceph-osd*.log",
            "/var/log/ceph/ceph-volume*.log",
        ])

        self.add_cmd_output([
            "ceph-disk list",
            "ceph-volume lvm list"
        ])

        ceph_cmds = [
           "bluestore bluefs available",
           "config diff",
           "config show",
           "dump_blacklist",
           "dump_blocked_ops",
           "dump_historic_ops_by_duration",
           "dump_historic_slow_ops",
           "dump_mempools",
           "dump_ops_in_flight",
           "dump_op_pq_state",
           "dump_osd_network",
           "dump_reservations",
           "dump_watchers",
           "log dump",
           "perf dump",
           "perf histogram dump",
           "objecter_requests",
           "ops",
           "status",
           "version",
        ]

        osd_ids = []
        # Get the ceph user processes
        out = self.exec_cmd('ps -u ceph -o args')

        if out['status'] == 0:
            # Extract the OSD ids from valid output lines
            for procs in out['output'].splitlines():
                proc = procs.split()
                # Locate the '--id' value
                if proc and proc[0].endswith("ceph-osd"):
                    try:
                        id_index = proc.index("--id")
                        osd_ids.append("osd.%s" % proc[id_index+1])
                    except (IndexError, ValueError):
                        self.log_warn("could not find ceph-osd id: %s", procs)

        try:
            cname = self.get_all_containers_by_regex("ceph-osd*")[0][1]
        except Exception:
            cname = None

        self.add_cmd_output(
            ["ceph daemon %s %s" % (i, c) for i in osd_ids for c in ceph_cmds],
            container=cname
        )

        self.add_forbidden_path([
            "/etc/ceph/*keyring*",
            "/var/lib/ceph/*keyring*",
            "/var/lib/ceph/*/*keyring*",
            "/var/lib/ceph/*/*/*keyring*",
            # Excludes temporary ceph-osd mount location like
            # /var/lib/ceph/tmp/mnt.XXXX from sos collection.
            "/var/lib/ceph/tmp/*mnt*",
            "/etc/ceph/*bindpass*"
        ])

# vim: set et ts=4 sw=4 :
