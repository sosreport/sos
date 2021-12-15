# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin
import glob


class CephMDS(Plugin, RedHatPlugin, UbuntuPlugin):
    short_desc = 'CEPH mds'
    plugin_name = 'ceph_mds'
    profiles = ('storage', 'virt', 'container')
    containers = ('ceph-fs.*',)

    def check_enabled(self):
        return True if glob.glob('/var/lib/ceph/mds/*/*') else False

    def setup(self):
        self.add_file_tags({
            '/var/log/ceph/ceph-mds.*.log': 'ceph_mds_log',
        })

        self.add_copy_spec([
            "/var/log/ceph/ceph-mds*.log",
            "/var/lib/ceph/bootstrap-mds/",
            "/var/lib/ceph/mds/",
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

        ceph_cmds = [
            "cache status",
            "client ls",
            "config diff",
            "config show",
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
            "perf histogram dump",
            "perf histogram schema",
            "perf schema",
            "perf dump",
            "status",
            "version",
            "session ls"
        ]

        mds_ids = []
        # Get the ceph user processes
        out = self.exec_cmd('ps -u ceph -o args')

        if out['status'] == 0:
            # Extract the OSD ids from valid output lines
            for procs in out['output'].splitlines():
                proc = procs.split()
                if len(proc) < 6:
                    continue
                if proc[4] == '--id' and "ceph-mds" in proc[0]:
                    mds_ids.append("mds.%s" % proc[5])

        # If containerized, run commands in containers
        try:
            cname = self.get_all_containers_by_regex("ceph-mds*")[0][1]
        except Exception:
            cname = None

        self.add_cmd_output([
            "ceph daemon %s %s"
            % (mdsid, cmd) for mdsid in mds_ids for cmd in ceph_cmds
        ], container=cname)


# vim: set et ts=4 sw=4 :
