# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

import os
import tempfile

from sos.report.plugins import Plugin, PluginOpt, UbuntuPlugin, DebianPlugin


class CharmedMySQLK8s(Plugin, UbuntuPlugin, DebianPlugin):
    """
    The Charmed MySQL K8s plugin is used to collect MySQL configuration and
    logs from the Charmed MySQL on Kubernets. It also collects MySQL Router
    and MySQL Shell configuration and logs where available,
    journal logs for the snap, and snap info.

    If the `dumpdbs` option is set to `True`, the plugin will also try and
    collect the names of the databases that the user has access to. The
    `mysql` user is used by default, but that can be set using the `dbuser`
    option. When using the `dumpdbs` option, you must then provide the
    password for the user using the `dbpass` option.
    """

    short_desc = "Charmed MySQL on Kubernetes"
    plugin_name = "charmed_mysql_k8s"
    packages = ("juju",)

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
        "show global status like \\\"%conne%\\\";",

        # Get errors per client and host
        # Useful for problens like an app disconnectting randomly
        "select * from performance_schema.host_cache;",

        # Get InnoDB status for any deadlocks, etc.
        "show ENGINE InnoDB STATUS;",
    ]

    mysql_conf_paths = {
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
            desc="How far back to fetch logs with kubectl --since"
        ),
    ]

    kube_cmd = "kubectl"
    selector = "app.kubernetes.io/name=mysql-k8s"

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
        for name, path in self.mysql_conf_paths.items():
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
        for pod in pods:
            self.add_copy_spec(f"{dump_files_path}/{pod}/*")

        # If dumpdbs is set, then get all databases
        if self.get_option("dumpdbs"):
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
                return

            opts = f"-h 127.0.0.1 -u{db_user}"
            sql_cmd = f"mysql {opts} -e"
            queries = " ".join(self.mysql_queries)

            with tempfile.TemporaryDirectory() as tmpdir:
                pwd_file = "mysql_pwd"
                pwd_path = tmpdir + "/" + pwd_file
                container_pwd_path = f"/tmp/{pwd_file}"

                with open(pwd_path, "w", encoding="utf8") as f:
                    f.write(db_pass)

                for pod in pods:
                    copy_cmd = (
                        f"{kube_cmd} cp -c {mysql_cont} "
                        f"{pwd_path} {pod}:{container_pwd_path}"
                    )
                    self.exec_cmd(copy_cmd)

                    queries_cmd = (
                        f"{kube_cmd} exec -c {mysql_cont} {pod} -- sh -lc "
                        f"'MYSQL_PWD=$(cat {container_pwd_path}) "
                        f"{sql_cmd} \"{queries}\"'"
                    )
                    self.add_cmd_output(
                        queries_cmd,
                        suggest_filename=f"{pod}_mysql_dbs.txt",
                    )

                    rm_cmd = (
                        f"{kube_cmd} exec -c {mysql_cont} {pod} -- rm "
                        f"{container_pwd_path}"
                    )
                    self.exec_cmd(rm_cmd)

    def setup(self):
        logs_since = self.get_option("logs_since")
        namespaces = self._determine_namespaces()
        for namespace in namespaces:
            self._collect_per_namespace(namespace, logs_since)


# vim: set et ts=4 sw=4 :
