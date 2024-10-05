# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class CephMON(Plugin, RedHatPlugin, UbuntuPlugin):
    """
    This plugin serves to collect information on monitor nodes within a Ceph
    or microceph cluster. It is designed to collect from several versions of
    Ceph, including versions that serve as the basis for RHCS 4 and RHCS 5.

    Older versions of Ceph will have collections from locations such as
    /var/log/ceph, whereas newer versions (as of this plugin's latest update)
    will have collections from /var/log/ceph/<fsid>/. This plugin attempts to
    account for this where possible across the host's filesystem.

    Users may expect to see several collections twice - once in standard output
    from the `ceph` command, and again in JSON format. The latter of which will
    be placed in the `json_output/` subdirectory within this plugin's directory
    in the report archive. These JSON formatted collections are intended to
    aid in automated analysis.
    """

    short_desc = 'CEPH mon'

    plugin_name = 'ceph_mon'
    profiles = ('storage', 'virt', 'container', 'ceph')
    # note: for RHCS 5 / Ceph v16 the containers serve as an enablement trigger
    # but by default they are not capable of running various ceph commands in
    # this plugin - the `ceph` binary is functional directly on the host
    containers = ('ceph-(.*-)?mon.*',)
    files = ('/var/lib/ceph/mon/*', '/var/lib/ceph/*/mon*',
             '/var/snap/microceph/common/data/mon/*')
    ceph_version = 0

    def setup(self):
        all_logs = self.get_option("all_logs")
        self.ceph_version = self.get_ceph_version()

        microceph_pkg = self.policy.package_manager.pkg_by_name('microceph')
        if not microceph_pkg:
            self.add_file_tags({
                '.*/ceph.conf': 'ceph_conf',
                "/var/log/ceph/(.*/)?ceph-.*mon.*.log": 'ceph_mon_log'
            })

            self.add_forbidden_path([
                "/etc/ceph/*keyring*",
                "/var/lib/ceph/**/*keyring*",
                # Excludes temporary ceph-osd mount location like
                # /var/lib/ceph/tmp/mnt.XXXX from sos collection.
                "/var/lib/ceph/**/tmp/*mnt*",
                "/etc/ceph/*bindpass*"
            ])

            if not all_logs:
                self.add_copy_spec([
                    "/var/log/ceph/**/*ceph-mon*.log"
                ])
            else:
                self.add_copy_spec([
                    "/var/log/ceph/**/*ceph-mon*.log*"
                ])

            self.add_copy_spec([
                "/run/ceph/**/ceph-mon*",
                "/var/lib/ceph/**/kv_backend",
            ])

        else:
            self.add_forbidden_path([
                "/var/snap/microceph/common/**/*keyring*",
                "/var/snap/microceph/current/**/*keyring*",
                "/var/snap/microceph/common/data/mon/*/store.db",
                "/var/snap/microceph/common/state/*",
            ])

            if not all_logs:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/*ceph-mon*.log",
                ])
            else:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/*ceph-mon*.log*",
                ])

            self.add_copy_spec([
                "/var/snap/microceph/common/data/mon/*",
                "/var/snap/microceph/current/conf/*",
            ])

        self.add_cmd_output("ceph report", tags="ceph_report")
        self.add_cmd_output([
            # The ceph_mon plugin will collect all the "ceph ..." commands
            # which typically require the keyring.

            "ceph config dump",
            "ceph config generate-minimal-conf",
            "ceph config log",
            "ceph config-key dump",
            "ceph crash ls",
            "ceph crash stat",
            "ceph features",
            "ceph health detail",
            "ceph insights",
            "ceph log last 10000 debug audit",
            "ceph log last 10000 debug cluster",
            "ceph mgr dump",
            "ceph mgr metadata",
            "ceph mgr module ls",
            "ceph mgr services",
            "ceph mgr versions",
            "ceph mon stat",
            "ceph mon features ls",
            "ceph node ls",
            "ceph osd crush class ls",
            "ceph osd crush dump",
            "ceph osd crush rule ls",
            "ceph osd crush show-tunables",
            "ceph osd crush tree --show-shadow",
            "ceph osd erasure-code-profile ls",
            "ceph osd metadata",
            "ceph osd utilization",
            "ceph telemetry channel ls",
            "ceph telemetry collection ls",
            "ceph telemetry ls",
            "ceph quorum_status",
            "ceph versions",
            "ceph-disk list",
        ])

        crashes = self.collect_cmd_output('ceph crash ls')
        if crashes['status'] == 0:
            for crashln in crashes['output'].splitlines():
                if crashln.endswith('*'):
                    cid = crashln.split()[0]
                    self.add_cmd_output(f"ceph crash info {cid}")

        ceph_cmds = [
            "device ls",
            "df detail",
            "df",
            "fs dump",
            "fs ls",
            "fs status",
            "mds stat",
            "mon dump",
            "osd blocked-by",
            "osd blocklist ls",
            "osd df tree",
            "osd df",
            "osd dump",
            "osd numa-status",
            "osd perf",
            "osd pool autoscale-status",
            "osd pool ls detail",
            "osd stat",
            "pg dump",
            "pg stat",
            "status",
            "time-sync-status",
        ]

        self.add_cmd_output("ceph health detail --format json-pretty",
                            subdir="json_output",
                            tags="ceph_health_detail")
        self.add_cmd_output("ceph osd tree --format json-pretty",
                            subdir="json_output",
                            tags="ceph_osd_tree")
        self.add_cmd_output(
            [f"ceph tell mon.{mid} mon_status" for mid in self.get_ceph_ids()],
            subdir="json_output",
        )

        self.add_cmd_output([f"ceph {cmd}" for cmd in ceph_cmds])

        # get ceph_cmds again as json for easier automation parsing
        self.add_cmd_output(
            [f"ceph {cmd} --format json-pretty" for cmd in ceph_cmds],
            subdir="json_output",
        )

    def get_ceph_version(self):
        """ Get the versions of running daemons """

        ver = self.exec_cmd('ceph --version')
        if ver['status'] == 0:
            try:
                _ver = ver['output'].split()[2]
                return int(_ver.split('.')[0])
            except Exception as err:  # pylint: disable=broad-except
                self._log_debug(f"Could not determine ceph version: {err}")
        self._log_error(
            'Failed to find ceph version, command collection will be limited'
        )
        return 0

    def get_ceph_ids(self):
        """ Get the IDs of the Ceph daemons """

        ceph_ids = []
        # ceph version 14 correlates to RHCS 4
        if self.ceph_version in (14, 15):
            # Get the ceph user processes
            out = self.exec_cmd('ps -u ceph -o args')

            if out['status'] == 0:
                # Extract the mon ids
                for procs in out['output'].splitlines():
                    proc = procs.split()
                    # Locate the '--id' value of the process
                    if proc and proc[0].endswith("ceph-mon"):
                        try:
                            id_index = proc.index("--id")
                            ceph_ids.append(proc[id_index + 1])
                        except (IndexError, ValueError):
                            self._log_warn('Unable to find ceph IDs')

        # ceph version 16 is RHCS 5
        elif self.ceph_version >= 16:
            stats = self.exec_cmd('ceph status')
            if stats['status'] == 0:
                try:
                    ret = re.search(r'(\s*mon: .* quorum) (.*) (\(.*\))',
                                    stats['output'])
                    ceph_ids.extend(ret.groups()[1].split(','))
                except Exception as err:  # pylint: disable=broad-except
                    self._log_debug(f"id determination failed: {err}")
        return ceph_ids

    def postproc(self):

        if self.ceph_version >= 16:
            keys = [
                'key',
                'username',
                'password',
                '_secret',
                'rbd/mirror/peer/.*'
            ]
            # we need to do this iteratively, as config-key dump here contains
            # nested json data written as strings, which may have multiple hits
            # within the same line
            for key in keys:
                creg = fr'(((.*)({key}\\\": ))((\\\"(.*?)\\\")(.*)))'
                self.do_cmd_output_sub(
                        'ceph config-key dump', creg, r'\2\"******\"\8'
                )
        else:
            keys = [
                'API_PASSWORD',
                'API_USER.*',
                'API_.*_KEY',
                'key',
                '_secret',
                'rbd/mirror/peer/.*'
            ]

            creg = fr"((\".*({'|'.join(keys)})\":) \")(.*)(\".*)"
            self.do_cmd_output_sub(
                    'ceph config-key dump', creg, r'\1*******\5'
            )

        self.do_cmd_private_sub('ceph config-key dump')

# vim: set et ts=4 sw=4 :
