# Copyright (C) 2025 Canonical Ltd.,
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
from sos.report.plugins import Plugin, IndependentPlugin, SoSPredicate


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

    def generate_sql_cmd(self, cfg, query_entry):
        """Prepare the sql command based on application, supplied command
        options, database locality, and query to be executed"""

        pkg = cfg.get("pkg")
        sql_cmd = cfg.get('sql_cmd')
        opts = query_entry.get("opts", [])
        db = query_entry.get("db", "local")

        # lxd's built-in command requires specifying local or global db
        if pkg == "lxd":
            sql_cmd = f"{sql_cmd} {db}"

        # Passthrough command flags / options
        for opt in opts:
            sql_cmd = f"{sql_cmd} {opt}"

        query = json.dumps(query_entry.get("query"))

        return f"{sql_cmd} {query}"

    def run_batch_dqlite_queries(self, cfg):
        """Execute the set of applicable sql queries for an application"""

        pkg = cfg.get("pkg")
        predicate = cfg.get("predicate")
        queries = cfg.get("queries")

        for query_entry in queries:
            file_suffix = query_entry.get("suggested_file_suffix")

            sql_cmd = self.generate_sql_cmd(cfg, query_entry)
            self.add_cmd_output(
                sql_cmd,
                suggest_filename=f"{pkg}_sql_{file_suffix}",
                subdir=pkg,
                pred=predicate
            )

    def base_collection(self, cfg):
        """Conduct a baseline collection that is common for all dqlite-based
        applications, and share common sql queries amongst the relevant
        applications"""

        pkg = cfg.get("pkg")
        db_path = cfg.get("db_path")
        crt_dir = cfg.get("crt_dir")
        cert = f"{crt_dir}/cluster.crt"

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

        self.add_cmd_output(
            f"openssl x509 -in {cert} -noout -dates",
            subdir=pkg
        )

        # Determine queries to run based on installed package
        if pkg == "microk8s":
            # At this time, microk8s is rather divergent w.r.t querying
            return self.run_batch_dqlite_queries(cfg)

        cfg["queries"].extend([{
            "query": "SELECT * FROM sqlite_master WHERE type=\"table\";",
            "suggested_file_suffix": "schema",
        },])

        return self.run_batch_dqlite_queries(cfg)

    def microceph_collection(self, cfg):
        """ Currently empty, as nothing currently necessitates unique microceph
        dqlite collection. A no-op, present for future extension
        """
    def microovn_collection(self, cfg):
        """ Currently empty, as nothing currently necessitates unique microovn
        dqlite collection. A no-op, present for future extension
        """

    def microcloud_collection(self, cfg):
        """ Currently empty, as nothing currently necessitates unique
        microcloud dqlite collection. A no-op, present for future extension
        """

    def microk8s_collection(self, cfg):
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

        # microk8s does not have a built-in command for interfacing with the
        # dqlite instance, override it with a command using the dqlite binary
        cfg["sql_cmd"] = dqlite_cmd

        cfg["queries"].extend([
            {
                "query": ".cluster",
                "suggested_file_suffix": ".cluster",
            },
            {
                "query": ".cluster",
                "suggested_file_suffix": ".cluster_-f_json",
                "opts": ["-f json",],
            },
            {
                "query": ".leader",
                "suggested_file_suffix": ".leader",
            },
        ])

        try:
            with open(servers, 'r', encoding='utf-8') as cluster_definition:
                cluster = cluster_definition.read()
                nodes = re.findall(
                    r'Address:\s*(\d+\.\d+\.\d+\.\d+:\d+)', cluster
                )

                for node in nodes:
                    cfg["queries"].append({
                        "query": f".describe {node}",
                        "suggested_file_suffix": f".describe_{node}",
                        "opts": ["-f json",],
                    })

        except Exception as e:
            self.add_alert(f"Failed to parse {servers}: {e}")

    def lxd_collection(self, cfg):
        cfg["queries"].extend([
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
            {
                "query": "SELECT * FROM raft_nodes;",
                "suggested_file_suffix": "raft_nodes",
                "db": "local",
            },
        ])

    def generate_microcluster_pkg_map(self, pkg, collection, sql_cmd):
        """Programatically generate the information needed to conduct a
        collection of microceph, microovn, and microcloud. They are all driven
        by the same microcluster engine and follow similar patterns"""

        return {
            "pkg": pkg,
            "db_path": f"/var/snap/{pkg}/common/state/database",
            "crt_dir": f"/var/snap/{pkg}/common/state",
            "sql_cmd": sql_cmd,
            "collection": collection,
            "predicate": None,
            "queries": [
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
        }

    def setup(self):
        # Do not collect for lxd unless the necessary services are running
        lxd_pred = (
            SoSPredicate(
                self,
                services=['snap.lxd.daemon'],
                required={'services': 'all'}
            ) if self.is_snap_installed("lxd") else
            SoSPredicate(
                self,
                services=['lxd'],
                required={'services': 'all'}
            )
        )

        # For each package backed by dqlite, create a map of the necessary
        # properties to conduct a collection
        packages = {
            "microceph": self.generate_microcluster_pkg_map(
                pkg="microceph",
                collection=self.microceph_collection,
                sql_cmd="microceph cluster sql",
            ),
            "microovn": self.generate_microcluster_pkg_map(
                pkg="microovn",
                collection=self.microovn_collection,
                sql_cmd="microovn cluster sql",
            ),
            "microcloud": self.generate_microcluster_pkg_map(
                pkg="microcloud",
                collection=self.microcloud_collection,
                sql_cmd="microcloud sql",
            ),
            "microk8s": {
                "pkg": "microk8s",
                "db_path": "/var/snap/microk8s/current/var/kubernetes/backend",
                "crt_dir": "/var/snap/microk8s/current/var/kubernetes/backend",
                "sql_cmd": None,
                "collection": self.microk8s_collection,
                "predicate": None,
                "queries": [],
            },
            "lxd": {
                "pkg": "lxd",
                "db_path": "/var/snap/lxd/common/lxd/database/global",
                "crt_dir": "/var/snap/lxd/common/lxd",
                "sql_cmd": "lxd sql",
                "collection": self.lxd_collection,
                "predicate": lxd_pred,
                "queries": [],
            }
        }

        for pkg, config in packages.items():
            if self.is_installed(pkg):
                config.get("collection")(config)
                self.base_collection(config)

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

# vim: set et ts=4 sw=4 :
