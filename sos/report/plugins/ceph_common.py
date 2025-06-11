# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import json
from socket import gethostname
from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class CephCommon(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CEPH common'

    plugin_name = 'ceph_common'
    profiles = ('storage', 'virt', 'container', 'ceph')

    containers = ('ceph-(.*-)?(mon|rgw|osd).*',)
    ceph_hostname = gethostname()

    packages = (
        'ceph',
        'ceph-mds',
        'ceph-common',
        'libcephfs1',
        'ceph-fs-common',
        'calamari-server',
    )

    services = (
        'ceph-nfs@pacemaker',
        f'ceph-mds@{ceph_hostname}',
        f'ceph-mon@{ceph_hostname}',
        f'ceph-mgr@{ceph_hostname}',
        'ceph-radosgw@*',
        'ceph-osd@*'
    )

    # This check will enable the plugin regardless of being
    # containerized or not
    files = ('/etc/ceph/ceph.conf',
             '/var/snap/microceph/*',)

    def setup(self):
        all_logs = self.get_option("all_logs")

        microceph_pkg = self.policy.package_manager.pkg_by_name('microceph')
        if not microceph_pkg:
            self.add_file_tags({
                '.*/ceph.conf': 'ceph_conf',
                '/var/log/ceph(.*)?/ceph.log.*': 'ceph_log',
            })

            if not all_logs:
                self.add_copy_spec([
                    "/var/log/calamari/*.log",
                    "/var/log/ceph/**/ceph.log",
                    "/var/log/ceph/cephadm.log",
                ])
            else:
                self.add_copy_spec([
                    "/var/log/calamari",
                    "/var/log/ceph/**/ceph.log*",
                    "/var/log/ceph/cephadm.log*",
                ])

            self.add_copy_spec([
                "/var/log/ceph/**/ceph.audit.log*",
                "/etc/ceph/",
                "/etc/calamari/",
                "/var/lib/ceph/tmp/",
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
        else:
            if not all_logs:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/ceph.log",
                    "/var/snap/microceph/common/logs/ceph.audit.log",
                ])
            else:
                self.add_copy_spec([
                    "/var/snap/microceph/common/logs/ceph.log*",
                    "/var/snap/microceph/common/logs/ceph.audit.log*",
                ])

            self.add_cmd_output("snap info microceph", subdir="microceph")

            cmds = [
                'client config list',
                'cluster config list',
                'cluster list',
                'disk list',
                'log get-level',
                'status',
                'pool list',
                'remote list',
                'replication list rbd',
            ]

            self.add_cmd_output([f"microceph {cmd}" for cmd in cmds],
                                subdir='microceph')

            dqlite_crt = "/var/snap/microceph/common/state/cluster.crt"
            self.add_cmd_output(
                f"openssl x509 -in {dqlite_crt} -noout -dates",
                subdir="microceph"
            )

            db_path = "/var/snap/microceph/common/state/database"

            # Check for inconsistent dqlite db intervals
            self.add_dir_listing(
                db_path,
                suggest_filename="ls_microceph_dqlite_dir",
                subdir="microceph",
            )

            self.add_copy_spec([
                    f"{db_path}/info.yaml",
                    f"{db_path}/cluster.yaml",
                    f"{db_path}/../daemon.yaml",
            ])

            queries = [
                {
                    "query": (
                        "SELECT * FROM sqlite_master WHERE type=\"table\";"
                    ),
                    "suggested_file_suffix": "schema",
                },
                {
                    "query": (
                        "SELECT * FROM config WHERE NOT ( "
                        "key LIKE \"%keyring%\" OR "
                        "key LIKE \"%ca_cert%\" OR "
                        "key LIKE \"%ca_key%\" );"
                    ),
                    "suggested_file_suffix": "config",
                },
                {
                    "query": "SELECT * FROM services;",
                    "suggested_file_suffix": "services",
                },
                {
                    "query": (
                        "SELECT id, name, expiry_date "
                        "FROM core_token_records;"
                    ),
                    "suggested_file_suffix": "token_records",
                },
                {
                    "query": (
                        "SELECT id, name, address, schema_internal, "
                        "schema_external, heartbeat, role, api_extensions "
                        "FROM core_cluster_members;"
                    ),
                    "suggested_file_suffix": "core_cluster_members",
                },
                {
                    "query": "SELECT * FROM disks;",
                    "suggested_file_suffix": "disks",
                },
                {
                    "query": "SELECT * FROM client_config;",
                    "suggested_file_suffix": "client_config",
                },
                {
                    "query": "SELECT * FROM remote;",
                    "suggested_file_suffix": "remote",
                },
            ]

            for query_entry in queries:
                query = json.dumps(query_entry.get("query"))
                file_suffix = query_entry.get("suggested_file_suffix")
                self.add_cmd_output(
                    f"microceph cluster sql {query}",
                    suggest_filename=f"microceph_cluster_sql_{file_suffix}",
                    subdir="microceph"
                )

        self.add_cmd_output([
            "ceph -v",
        ])

    def postproc(self):
        protect_keys = [
            "rgw keystone admin password",
        ]
        regex = fr"(^({'|'.join(protect_keys)})\s*=\s*)(.*)"
        self.do_path_regex_sub("/etc/ceph/ceph.conf", regex, r"\1*********")

# vim: set et ts=4 sw=4 :
