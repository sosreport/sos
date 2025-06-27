# Copyright (C) 2023 Canonical Ltd.,
#                    David Negreira <david.negreira@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import re
from sos.report.plugins import Plugin, UbuntuPlugin


class Microk8s(Plugin, UbuntuPlugin):
    """The Microk8s plugin collects the current status of the microk8s
    snap on a Ubuntu machine.

    It will collect logs from journald related to the snap.microk8s
    units as well as run microk8s commands to retrieve the configuration,
    status, version and loaded plugins.
    """

    short_desc = 'The lightweight Kubernetes'
    plugin_name = "microk8s"
    profiles = ('container',)

    packages = ('microk8s',)

    microk8s_cmd = "microk8s"

    def setup(self):
        self.add_journal(units="snap.microk8s.*")

        microk8s_subcmds = [
            'addons repo list',
            'config',
            'ctr plugins ls',
            'ctr plugins ls -d',
            'status',
            'version'
        ]
        self.add_copy_spec([
            "/var/snap/microk8s/current/args/*",
            "/var/snap/microk8s/current/credentials/client.config",
        ])

        self.add_cmd_output([
            f"{self.microk8s_cmd} {subcmd}" for subcmd in microk8s_subcmds
        ])

        crt_dir = "/var/snap/microk8s/current/var/kubernetes/backend"
        dqlite_crt = f"{crt_dir}/cluster.crt"

        self.add_cmd_output(
            f"openssl x509 -in {dqlite_crt} -noout -dates",
        )

        db_path = "/var/snap/microk8s/current/var/kubernetes/backend"

        # Check for inconsistent dqlite db intervals
        self.add_dir_listing(
            db_path,
            suggest_filename="ls_microk8s_dqlite_dir",
        )

        self.add_copy_spec([
            f"{db_path}/info.yaml",
            f"{db_path}/cluster.yaml",
            f"{db_path}/failure-domain",
        ])

        dqlite_bin = "/snap/microk8s/current/bin/dqlite"
        cert = f"{db_path}/cluster.crt"
        key = f"{db_path}/cluster.key"
        servers = f"{db_path}/cluster.yaml"
        dqlite_cmd = f"{dqlite_bin} -c {cert} -k {key} -s file://{servers} k8s"

        queries = [
            {
                "query": ".cluster",
                "suggested_file_suffix": ".cluster",
            },
            {
                "query": ".cluster",
                "opts": ["-f json",],
                "suggested_file_suffix": ".cluster_-f_json",
            },
            {
                "query": ".leader",
                "suggested_file_suffix": ".leader",
            },
        ]

        try:
            with open(servers, 'r', encoding='utf-8') as cluster_definition:
                cluster = cluster_definition.read()
                nodes = re.findall(
                    r'Address:\s*(\d+\.\d+\.\d+\.\d+:\d+)', cluster
                )

                for node in nodes:
                    queries.append({
                        "query": f".describe {node}",
                        "suggested_file_suffix": f".describe_{node}",
                        "opts": ["-f json",],
                    })

        except Exception as e:
            self.add_alert(f"Failed to parse {servers}: {e}")

        for query_entry in queries:
            sql_cmd = dqlite_cmd
            opts = query_entry.get("opts", [])
            for opt in opts:
                sql_cmd = f"{sql_cmd} {opt}"

            query = json.dumps(query_entry.get("query"))
            file_suffix = query_entry.get("suggested_file_suffix")
            self.add_cmd_output(
                f"{sql_cmd} {query}",
                suggest_filename=f"microk8s_sql_{file_suffix}",
            )

    def postproc(self):
        rsub = r'(certificate-authority-data:|token:)\s.*'
        self.do_cmd_output_sub(self.microk8s_cmd, rsub, r'\1 "**********"')

        protect_keys = [
            "certificate-authority-data",
            "client-certificate-data",
            "client-key-data",
            "token",
        ]

        key_regex = fr'(^\s*({"|".join(protect_keys)})\s*:\s*)(.*)'

        self.do_path_regex_sub(
            "/var/snap/microk8s/current/credentials/client.config",
            key_regex, r"\1*********"
        )

# vim: set et ts=4 sw=4
