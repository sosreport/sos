# Copyright (C) 2024 Alan Baghumian <alan.baghumian@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
from sos.report.plugins import Plugin, UbuntuPlugin


class MicroOVN(Plugin, UbuntuPlugin):
    """The MicroOVN plugin collects the current status of the microovn
    snap.

    It will collect journald logs as well as output from various microovn
    commands.
    """

    short_desc = 'MicroOVN Snap'
    plugin_name = "microovn"
    profiles = ('network', 'virt')

    packages = ('microovn', )
    commands = ('microovn', )

    def setup(self):
        self.add_journal(units="snap.microovn.*")

        microovn_subcmds = [
            'cluster list',
            'status',
            'certificates list',
            '--version'
        ]
        self.add_cmd_output([
            f"microovn {subcmd}" for subcmd in microovn_subcmds
        ])

        dqlite_crt = "/var/snap/microovn/common/state/cluster.crt"
        self.add_cmd_output(
            f"openssl x509 -in {dqlite_crt} -noout -dates",
        )

        db_path = "/var/snap/microovn/common/state/database"

        # Check for inconsistent dqlite db intervals
        self.add_dir_listing(
            db_path,
            suggest_filename="ls_microovn_dqlite_dir",
        )

        self.add_copy_spec([
                f"{db_path}/info.yaml",
                f"{db_path}/cluster.yaml",
                f"{db_path}/../daemon.yaml",
        ])

        queries = [
            {
                "query": "SELECT * FROM sqlite_master WHERE type=\"table\";",
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
        ]

        for query_entry in queries:
            query = json.dumps(query_entry.get("query"))
            file_suffix = query_entry.get("suggested_file_suffix")
            self.add_cmd_output(
                f"microovn cluster sql {query}",
                suggest_filename=f"microovn_cluster_sql_{file_suffix}",
            )

# vim: set et ts=4 sw=4 :
