# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin
import glob


class CephMON(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH mon'

    plugin_name = 'ceph_mon'
    profiles = ('storage', 'virt', 'container')
    containers = ('ceph-mon.*',)

    def check_enabled(self):
        return True if glob.glob('/var/lib/ceph/mon/*/*') else False

    def setup(self):
        self.add_file_tags({
            '.*/ceph.conf': 'ceph_conf',
            '/var/log/ceph/ceph-mon.*.log': 'ceph_mon_log'
        })

        self.add_copy_spec([
            "/run/ceph/ceph-mon*",
            "/var/lib/ceph/mon/*/kv_backend",
            "/var/log/ceph/ceph-mon*.log"
        ])

        self.add_cmd_output([
            # The ceph_mon plugin will collect all the "ceph ..." commands
            # which typically require the keyring.

            "ceph mon stat",
            "ceph quorum_status",
            "ceph report",
            "ceph-disk list",
            "ceph versions",
            "ceph features",
            "ceph insights",
            "ceph crash stat",
            "ceph crash ls",
            "ceph config log",
            "ceph config generate-minimal-conf",
            "ceph config-key dump",
            "ceph osd metadata",
            "ceph osd erasure-code-profile ls",
            "ceph osd crush dump",
            "ceph osd crush show-tunables",
            "ceph osd crush tree --show-shadow",
            "ceph mgr dump",
            "ceph mgr metadata",
            "ceph mgr module ls",
            "ceph mgr services",
            "ceph mgr versions"
        ])

        ceph_cmds = [
            "mon dump",
            "status",
            "health detail",
            "device ls",
            "df",
            "df detail",
            "fs ls",
            "fs dump",
            "pg dump",
            "pg stat",
            "time-sync-status",
            "osd tree",
            "osd stat",
            "osd df tree",
            "osd dump",
            "osd df",
            "osd perf",
            "osd blocked-by",
            "osd pool ls detail",
            "osd pool autoscale-status",
            "mds stat",
            "osd numa-status"
        ]

        self.add_cmd_output([
            "ceph %s --format json-pretty" % s for s in ceph_cmds
        ], subdir="json_output", tags="insights_ceph_health_detail")

        mon_ids = []
        # Get the ceph user processes
        out = self.exec_cmd('ps -u ceph -o args')

        if out['status'] == 0:
            # Extract the mon ids
            for procs in out['output'].splitlines():
                proc = procs.split()
                # Locate the '--id' value of ceph-mon
                if proc and proc[0].endswith("ceph-mon"):
                    try:
                        id_index = proc.index("--id")
                        mon_ids.append(proc[id_index+1])
                    except (IndexError, ValueError):
                        self.log_warn("could not find ceph-mon id: %s", procs)

        self.add_cmd_output([
            "ceph tell mon.%s mon_status" % mon_id for mon_id in mon_ids
        ], subdir="json_output", tags="insights_ceph_health_detail")

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

        # If containerized, run commands in containers
        try:
            cname = self.get_all_containers_by_regex("ceph-mon*")[0][1]
        except Exception:
            cname = None

        self.add_cmd_output(
            ["ceph %s" % cmd for cmd in ceph_cmds],
            container=cname
        )

    def postproc(self):
        keys = [
            'API_PASSWORD',
            'API_USER.*',
            'API_.*_KEY',
            'key',
            '_secret',
            'rbd/mirror/peer/.*'
        ]

        creg = r"((\".*(%s)\":) \")(.*)(\".*)" % "|".join(keys)
        self.do_cmd_output_sub('ceph config-key dump', creg, r'\1*******\5')

# vim: set et ts=4 sw=4 :
