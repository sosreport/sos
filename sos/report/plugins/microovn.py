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

        queries = [
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
        ]

        for query_entry in queries:
            query = json.dumps(query_entry.get("query"))
            file_suffix = query_entry.get("suggested_file_suffix")
            self.add_cmd_output(
                f"microovn cluster sql {query}",
                suggest_filename=f"microovn_cluster_sql_{file_suffix}",
            )

# vim: set et ts=4 sw=4 :
