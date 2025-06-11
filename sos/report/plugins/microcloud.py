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


class MicroCloud(Plugin, UbuntuPlugin):
    """The MicroCloud plugin collects the current status of the microcloud
    snap.

    It will collect journald logs as well as output from various microcloud
    commands.
    """

    short_desc = 'MicroCloud Snap'
    plugin_name = "microcloud"
    profiles = ('container',)

    packages = ('microcloud',)

    def setup(self):
        self.add_journal(units="snap.microcloud.*")

        microcloud_subcmds = [
            'cluster list',
            'status',
            '--version'
        ]

        self.add_cmd_output([
            f"microcloud {subcmd}" for subcmd in microcloud_subcmds
        ])

        dqlite_crt = "/var/snap/microcloud/common/state/cluster.crt"

        self.add_cmd_output(
            f"openssl x509 -in {dqlite_crt} -noout -dates",
        )

        db_path = "/var/snap/microcloud/common/state/database"

        # Check for inconsistent dqlite db intervals
        self.add_dir_listing(
            db_path,
            suggest_filename="ls_microcloud_dqlite_dir",
        )

        self.add_copy_spec([
            f"{db_path}/cluster.yaml",
            f"{db_path}/info.yaml",
            f"{db_path}/../daemon.yaml",
        ])

        queries = [
            {
                "query": "SELECT * FROM sqlite_master WHERE type=\"table\";",
                "suggested_file_suffix": "schema",
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
                f"microcloud sql {query}",
                suggest_filename=f"microcloud_sql_{file_suffix}",
            )

# vim: set et ts=4 sw=4
