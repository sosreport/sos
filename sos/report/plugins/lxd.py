# Copyright (C) 2016 Jorge Niedbalski <niedbalski@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
from sos.report.plugins import Plugin, UbuntuPlugin, SoSPredicate


class LXD(Plugin, UbuntuPlugin):

    short_desc = 'LXD container hypervisor'
    plugin_name = 'lxd'
    profiles = ('container',)
    packages = ('lxd',)
    commands = ('lxc', 'lxd',)
    services = ('snap.lxd.daemon', 'snap.lxd.activate')

    def setup(self):

        lxc_cmds = [
            "lxc image list local:",
            "lxc list local:",
            "lxc network list local:",
            "lxc profile list local:",
            "lxc storage list local:",
            "lxc operation list local:",
            "lxc info local:",
            "lxc alias list",
            "lxc remote list",
            "lxc version local:",
            "lxc warning list local:",
            "lxc auth permission list local:",
            "lxc cluster list local:"
        ]

        if self.is_snap:

            lxd_pred = SoSPredicate(self, services=['snap.lxd.daemon'],
                                    required={'services': 'all'})

            self.add_cmd_output("lxd.buginfo", pred=lxd_pred, snap_cmd=True)

            self.add_copy_spec([
                '/var/snap/lxd/common/config',
                '/var/snap/lxd/common/global-conf',
                '/var/snap/lxd/common/lxc/local.conf',
                '/var/snap/lxd/common/lxd/logs/*/*.conf',
            ])

            if not self.get_option("all_logs"):
                self.add_copy_spec([
                    '/var/snap/lxd/common/lxd/logs/*.log',
                    '/var/snap/lxd/common/lxd/logs/*/*.log',
                ])
            else:
                self.add_copy_spec([
                    '/var/snap/lxd/common/lxd/logs/**',
                ])

            dqlite_crt = "/var/snap/lxd/common/lxd/cluster.crt"
            self.add_cmd_output(
                f"openssl x509 -in {dqlite_crt} -noout -dates",
            )

            db_path = "/var/snap/lxd/common/lxd/database/global"
            self.add_dir_listing(
                db_path,
                suggest_filename="ls_lxd_dqlite_dir",
            )

            queries = [
                {
                    "query": (
                        "SELECT * FROM sqlite_master WHERE type=\"table\";"
                    ),
                    "suggested_file_suffix": "schema",
                    "db": "local",
                },
                {
                    "query": (
                        "SELECT * FROM config WHERE NOT ( "
                        "key LIKE \"%keyring%\" OR "
                        "key LIKE \"%ca_cert%\" OR "
                        "key LIKE \"%ca_key%\" );"
                    ),
                    "suggested_file_suffix": "config",
                    "db": "local"
                },
                {
                    "query": "SELECT * FROM raft_nodes;",
                    "suggested_file_suffix": "raft_nodes",
                    "db": "local",
                },
                {
                    "query": "SELECT * FROM nodes;",
                    "suggested_file_suffix": "nodes",
                    "db": "global",
                },
                {
                    "query": "SELECT * FROM nodes_roles;",
                    "suggested_file_suffix": "nodes_roles",
                    "db": "global",
                },
            ]

            for query_entry in queries:
                db = query_entry.get("db", "local")
                query = json.dumps(query_entry.get("query"))
                file_suffix = query_entry.get("suggested_file_suffix")
                self.add_cmd_output(
                    f"lxd sql {db} {query}",
                    suggest_filename=f"lxd_sql_{db}_{file_suffix}",
                    pred=lxd_pred,
                )

        else:
            lxd_pred = SoSPredicate(self, services=['lxd'],
                                    required={'services': 'all'})
            self.add_copy_spec([
                "/etc/default/lxd-bridge",
                "/var/log/lxd/*"
            ])

            self.add_cmd_output([
                "find /var/lib/lxd -maxdepth 2 -type d -ls",
            ], suggest_filename='var-lxd-dirs.txt')

        self.add_cmd_output(lxc_cmds, pred=lxd_pred, snap_cmd=self.is_snap)

    def postproc(self):
        self.do_cmd_private_sub('lxd.buginfo')

# vim: set et ts=4 sw=4 :
