# Copyright (C) 2023 Canonical Ltd.,
#                    Bryan Fraschetti <bryan.fraschetti@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import re
from sos.report.plugins import Plugin, IndependentPlugin


class dqlite(Plugin, IndependentPlugin):
    """Dqlite (distributed SQLite) extends SQLite across a cluster of machines,
    with automatic failover and high-availability to keep your application
    running. It uses C-Raft, an optimised Raft implementation in C, to gain
    high-performance transactional consensus and fault tolerance while
    preserving SQlite’s outstanding efficiency and tiny footprint.
    """

    short_desc = 'Distributed embedded sqlite database library'
    plugin_name = "dqlite"
    profiles = ('storage', 'cluster',)

    packages = ('microk8s', 'microceph', 'microovn', 'microcloud', 'lxd',)

    def postproc(self):

        # Remove microk8s certificate data from config file
        protect_keys = [
            "certificate-authority-data",
            "client-certificate-data",
            "client-key-data",
        ]

        regexp = fr"^\s*(#?\s*({'|'.join(protect_keys)}):\s*)(\S.*)"

        self.do_file_sub(
            "/var/snap/microk8s/current/credentials/client.config",
            regexp,
            r"\1 ******",
        )

    def run_batch_dqlite_queries(self, pkg, cfg, queries, tables):
        sql_cmd = cfg.get("sql_cmd")
        sock = cfg.get("socket")
        endpoint = cfg.get("socket_endpoint")
        header = "Content-Type: application/json"

        curl_cmd = f"""
            curl -s --unix-socket {sock} \
                -X POST {endpoint} \
                -H \"{header}\" \
                -d
            """

        for query, table in zip(queries, tables):
            query_json = json.dumps(
                {"query": query, "database": "local"} if pkg == "lxd"
                else {"query": query}
            )
            socket_cmd = f"{curl_cmd} '{query_json}'"

            self.add_cmd_output(
                socket_cmd,
                suggest_filename=f"{pkg}_dqlite_{table}",
                subdir=pkg,
            )

            if sql_cmd:
                self.add_cmd_output(
                    f"{sql_cmd} {json.dumps(query)}",
                    suggest_filename=f"{sql_cmd}_{table}",
                    subdir=pkg,
                )

    def base_collection(self, pkg, cfg):
        db_path = cfg.get("db_path")

        # Check for inconsistent dqlite db intervals
        self.add_dir_listing(
            db_path,
            suggest_filename=f"ls_{pkg}_dqlite_dir",
            subdir=pkg,
        )

        # All dqlite consumers except lxd have info.yaml and cluster.yaml
        self.add_copy_spec(
            [
                f"{db_path}/info.yaml",
                f"{db_path}/cluster.yaml",
                f"{db_path}/../daemon.yaml",  # Not expected for microk8s
            ]
        )

        # Determine queries to run based on installed package
        if pkg == "microk8s":
            # At this time, microk8s is rather divergent w.r.t querying
            return

        queries = [
            "SELECT * FROM sqlite_master WHERE type=\"table\";",
        ]
        tables = ["schema",]  # Table name will be used in filename

        if pkg not in ("lxd",):
            queries.extend([
                "SELECT id, name, expiry_date FROM core_token_records;",
                "SELECT id, name, address, schema_internal, \
                    schema_external, heartbeat, role, api_extensions \
                    FROM core_cluster_members;",
            ])
            tables.extend(["token_records", "core_cluster_members",])

        if pkg not in ("microcloud",):
            queries.extend([
                "SELECT * FROM config WHERE NOT ( \
                    key LIKE \"%keyring%\" OR \
                    key LIKE \"%ca_cert%\" OR \
                    key LIKE \"%ca_key%\" \
                );",
            ])
            tables.extend(["config",])

        if pkg in ("microceph", "microovn",):
            queries.extend(["SELECT * FROM services;",])
            tables.extend(["services",])

        self.run_batch_dqlite_queries(pkg, cfg, queries, tables)

    def microceph_collection(self, pkg, cfg):
        queries = [
            "SELECT * FROM disks;",
            "SELECT * FROM client_config;",
            "SELECT * FROM remote;",
        ]

        tables = ["disks", "client_config", "remote",]

        self.run_batch_dqlite_queries(pkg, cfg, queries, tables)

    def microovn_collection(self, pkg, cfg):
        """ Currently empty, as nothing currently necessitates unique microovn
        dqlite collection. A no-op, present for future extension
        """

    def microcloud_collection(self, pkg, cfg):
        """ Currently empty, as nothing currently necessitates unique
        microcloud dqlite collection. A no-op, present for future extension
        """

    def microk8s_collection(self, pkg, cfg):
        db_path = cfg.get("db_path")

        self.add_copy_spec([
            "/var/snap/microk8s/current/credentials/client.config",
            f"{db_path}/failure-domain",
        ])

        dqlite_bin = "/snap/microk8s/current/bin/dqlite"
        cert = f"{db_path}/cluster.crt"
        key = f"{db_path}/cluster.key"
        servers = f"{db_path}/cluster.yaml"
        dqlite_cmd = f"{dqlite_bin} -c {cert} -k {key} -s file://{servers} k8s"

        queries = [
            "\".cluster\"",
            "\".cluster\" -f json",
            "\".leader\"",
        ]

        suggested_names = [
            f"{pkg}_dqlite_{query}" for query in queries
        ]

        try:
            with open(servers, 'r', encoding='utf-8') as cluster_definition:
                cluster = cluster_definition.read()
                nodes = re.findall(
                    r'Address:\s*(\d+\.\d+\.\d+\.\d+:\d+)', cluster
                )

                for node in nodes:
                    queries.append(
                        f"\".describe {node}\" -f json"
                    )
                    suggested_names.append(
                        f"{pkg}_dqlite_.describe_{node}"
                    )
        except Exception as e:
            self.add_alert(f"Failed to parse {servers}: {e}")

        for query, suggested_name in zip(queries, suggested_names):
            self.add_cmd_output(
                f"{dqlite_cmd} {query}",
                suggest_filename=suggested_name,
                subdir=pkg,
            )

    def lxd_collection(self, pkg, cfg):
        """ Currently empty, as nothing currently necessitates unique
        lxd dqlite collection. A no-op, present for future extension
        """

    def setup(self):
        packages = {
            "microceph": {
                "db_path": "/var/snap/microceph/common/state/database",
                "socket": "/var/snap/microceph/common/state/control.socket",
                "sql_cmd": "microceph cluster sql",
                "socket_endpoint": "microceph/core/internal/sql",
                "collection": self.microceph_collection,
            },
            "microovn": {
                "db_path": "/var/snap/microovn/common/state/database",
                "socket": "/var/snap/microovn/common/state/control.socket",
                "sql_cmd": "microovn cluster sql",
                "socket_endpoint": "microovn/core/internal/sql",
                "collection": self.microovn_collection,
            },
            "microcloud": {
                "db_path": "/var/snap/microcloud/common/state/database",
                "socket": "/var/snap/microcloud/common/state/control.socket",
                "sql_cmd": "microcloud sql",
                "socket_endpoint": "microcloud/core/internal/sql",
                "collection": self.microcloud_collection,
            },
            "microk8s": {
                "db_path": "/var/snap/microk8s/current/var/kubernetes/backend",
                "socket": "/var/snap/microk8s/current/var/kubernetes/backend/"
                "kine.sock:12379",
                "sql_cmd": None,
                "socket_endpoint": "microk8s/core/internal/sql",
                "collection": self.microk8s_collection,
            },
            "lxd": {
                "db_path": "/var/snap/lxd/common/lxd/database/global",
                "socket": "/var/snap/lxd/common/lxd/unix.socket",
                "sql_cmd": "lxd sql local",
                "socket_endpoint": "lxd/internal/sql",
                "collection": self.lxd_collection,
            }
        }

        for pkg, config in packages.items():
            if self.is_installed(pkg):
                self.base_collection(pkg, config)
                config.get("collection")(pkg, config)

# vim: set et ts=4 sw=4 :
