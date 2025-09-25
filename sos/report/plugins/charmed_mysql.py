# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

import os
import tempfile

from sos.report.plugins import Plugin, PluginOpt, UbuntuPlugin
from sos.utilities import is_executable


class CharmedMySQL(Plugin, UbuntuPlugin):
    """
    The Charmed MySQL plugin is used to collect MySQL configuration and logs
    from the Charmed MySQL snap package or K8s deployment.
    It also collects MySQL Router and MySQL Shell configuration and logs
    where available, journal logs for the snap, and snap info.

    If the `dumpdbs` option is set to `True`, the plugin will also try and
    collect the names of the databases that the user has access to. The
    `mysql` user is used by default, but that can be set using the `dbuser`
    option. When using the `dumpdbs` option, you must then provide the
    password for the user using the `dbpass` option or the `MYSQL_PWD`
    environment variable.
    """

    short_desc = "Charmed MySQL"
    plugin_name = "charmed_mysql"

    mysql_queries = [
        # Get databases user has access to
        "show databases;",

        # Get unit operations from MySQL to see, for example,
        # if a unit is stuck on joining the cluster
        "select * from mysql.juju_units_operations;",

        # Get the cluster group replication status
        ("select * from performance_schema.replication_group_members "
            "order by MEMBER_HOST;"),

        # Get connection stats
        "show global status like \"%conne%\";",

        # Get errors per client and host
        # Useful for problens like an app disconnectting randomly
        "select * from performance_schema.host_cache;",

        # Get InnoDB status for any deadlocks, etc.
        "show ENGINE InnoDB STATUS;",
    ]

    snap_package = "charmed-mysql"
    snap_path_common = "/var/snap/charmed-mysql/common"
    snap_path_current = "/var/snap/charmed-mysql/current"

    kube_cmd = "kubectl"
    selector = "app.kubernetes.io/name=mysql-k8s"

    conf_paths = {
        "MYSQL_CONF": "/etc/mysql",
        "MYSQL_LOGS": "/var/log/mysql",
        "MYSQL_ROUTER_CONF": "/etc/mysqlrouter",
        "MYSQL_ROUTER_LOGS": "/var/log/mysqlrouter",
        "MYSQL_SHELL_LOGS": "/var/log/mysqlsh",
    }

    option_list = [
        PluginOpt(
            "dbuser", default="mysql", val_type=str,
            desc="Username for database dump collection"
        ),
        PluginOpt(
            "dbpass", default="", val_type=str,
            desc="Password for database dump collection",
        ),
        PluginOpt(
            "dumpdbs", default=False, val_type=bool,
            desc="Get name of all databases"
        ),
        PluginOpt(
            "logs_since", default="48h", val_type=str,
            desc="How far back to fetch logs with kubectl --since, K8s only"
        ),
    ]

    def _get_db_credentials(self):
        db_user = self.get_option("dbuser")
        db_pass = self.get_option("dbpass")

        if "MYSQL_PWD" in os.environ and not db_pass:
            self.soslog.info(
                "MYSQL_PWD present: Using MYSQL_PWD environment variable, "
                "user did not provide password."
            )
            db_pass = os.environ["MYSQL_PWD"]
        elif not db_pass:
            self.soslog.warning(
                "dumpdbs_error: option is set, but username and password "
                "are not provided"
            )
            return None, None

        return db_user, db_pass

    def _determine_namespaces(self):
        namespaces = self.exec_cmd(
            f"{self.kube_cmd} get pods -A -l {self.selector} "
            "-o jsonpath='{.items[*].metadata.namespace}'"
        )
        if namespaces['status'] == 0:
            return list(set(namespaces['output'].strip().split()))
        return []

    def _get_pod_names(self, namespace):
        pods = self.exec_cmd(
            f"{self.kube_cmd} -n {namespace} get pods -l {self.selector} "
            "-o jsonpath='{.items[*].metadata.name}'"
        )
        if pods['status'] == 0:
            return pods['output'].strip().split()
        return []

    def _collect_per_namespace(self, namespace, logs_since):
        kube_cmd = f"{self.kube_cmd} -n {namespace}"

        # Describe the resources
        self.add_cmd_output([
            f"{kube_cmd} get all -l {self.selector} -o wide",
            f"{kube_cmd} describe pods -l {self.selector}",
        ])

        # Get pod logs
        self.add_cmd_output(
            f"{kube_cmd} logs -l {self.selector} --since={logs_since} "
            "--all-containers=true --prefix --all-pods"
        )

        mysql_cont = "mysql"
        pods = self._get_pod_names(namespace)

        # Get the config and logs from each pod
        dump_files_path = self.get_cmd_output_path()
        for name, path in self.conf_paths.items():
            for pod in pods:
                os.makedirs(f"{dump_files_path}/{pod}/{name}", exist_ok=True)
                copy_cmd = (
                    f"{kube_cmd} cp -c {mysql_cont} {pod}:{path} "
                    f"{dump_files_path}/{pod}/{name}"
                )
                self.exec_cmd(copy_cmd)

        self.add_forbidden_path([
            f"{dump_files_path}/*/MYSQL_CONF/*.pem",
            f"{dump_files_path}/*/MYSQL_CONF/*.key",
        ])

        # If dumpdbs is set, then get all databases
        if self.get_option("dumpdbs"):
            db_user, db_pass = self._get_db_credentials()
            if not db_user or not db_pass:
                return

            opts = f"-h 127.0.0.1 -u{db_user}"
            sql_cmd = f"mysql {opts} -e"
            queries = " ".join(
                query.replace('\"', '\\\"')
                for query in self.mysql_queries
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                pwd_file = "mysql_pwd"
                pwd_path = tmpdir + "/" + pwd_file

                with open(pwd_path, "w", encoding="utf8") as f:
                    f.write(db_pass)

                for pod in pods:
                    mkdir_cmd = (
                        f"{kube_cmd} exec -c {mysql_cont} {pod} -- "
                        f"mkdir -p {tmpdir}"
                    )
                    self.exec_cmd(mkdir_cmd)

                    copy_cmd = (
                        f"{kube_cmd} cp -c {mysql_cont} "
                        f"{pwd_path} {pod}:{pwd_path}"
                    )
                    self.exec_cmd(copy_cmd)

                    queries_cmd = (
                        f"{kube_cmd} exec -c {mysql_cont} {pod} -- "
                        f"sh -lc 'MYSQL_PWD=$(cat {pwd_path}) "
                        f"{sql_cmd} \"{queries}\"' "
                        f"&& rm -rf {tmpdir}"
                    )
                    self.add_cmd_output(
                        queries_cmd,
                        suggest_filename=f"{pod}_dbs.txt",
                    )

    def _join_conf_path(self, base, *parts):
        stripped_parts = [p.lstrip(os.path.sep) for p in parts]
        return os.path.join(base, *stripped_parts)

    def _process_k8s(self):
        logs_since = self.get_option("logs_since")
        namespaces = self._determine_namespaces()
        for namespace in namespaces:
            self._collect_per_namespace(namespace, logs_since)

    def _process_snap(self):
        # Ignore private keys
        self.add_forbidden_path([
            self._join_conf_path(
                self.snap_path_current,
                self.conf_paths["MYSQL_CONF"],
                "*.pem"
            ),
            self._join_conf_path(
                self.snap_path_current,
                self.conf_paths["MYSQL_CONF"],
                "*.key"
            ),
        ])

        # Include the files we want to get
        self.add_copy_spec([
            self._join_conf_path(
                self.snap_path_current,
                self.conf_paths["MYSQL_CONF"]
            ),
            self._join_conf_path(
                self.snap_path_common,
                self.conf_paths["MYSQL_LOGS"]
            ),
            self._join_conf_path(
                self.snap_path_current,
                self.conf_paths["MYSQL_ROUTER_CONF"]
            ),
            self._join_conf_path(
                self.snap_path_common,
                self.conf_paths["MYSQL_ROUTER_LOGS"]
            ),
            self._join_conf_path(
                self.snap_path_common,
                self.conf_paths["MYSQL_SHELL_LOGS"]
            ),
        ])

        # Get snap logs
        self.add_journal("snap.charmed-mysql.*")

        # Get snap info
        self.add_cmd_output("snap info charmed-mysql")

        # If dumpdbs is set, then get all databases
        if self.get_option("dumpdbs"):
            db_user, db_pass = self._get_db_credentials()
            if not db_user or not db_pass:
                return

            mysql_env = {"MYSQL_PWD": db_pass}
            opts = f"-h 127.0.0.1 -u{db_user}"
            sql_cmd = f"mysql {opts} -e"

            self.add_cmd_output(
                [f"{sql_cmd} '{query}'" for query in self.mysql_queries],
                env=mysql_env,
            )

    def check_enabled(self):
        # Check for snap package
        if self.is_installed(self.snap_package):
            return True

        # Check for kubectl and pods
        return (
            is_executable(self.kube_cmd, self.sysroot) and
            bool(self._determine_namespaces())
        )

    def setup(self):
        if self.is_installed(self.snap_package):
            self._process_snap()

        if is_executable(self.kube_cmd, self.sysroot):
            self._process_k8s()

# vim: set et ts=4 sw=4 :
