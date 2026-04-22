# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

from enum import Enum
import shutil
from urllib.parse import quote, quote_plus, urlencode
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml

from sos.report.plugins import Plugin, PluginOpt, UbuntuPlugin
from sos.utilities import is_executable

DATE_FORMAT = "%Y-%m-%d-%H"


class Substrate(Enum):
    VM = "vm"
    K8S = "k8s"


class CharmedMongos(Plugin, UbuntuPlugin):
    """The Charmed Mongos plugin is used to collect Mongos configuration
    and logs from the Charmed Mongos snap package or K8s deployment.

    If all_logs is set to True, it collects all logs by default.
    The parameters `dbuser` and `dbpass` are used to dump database information,
    replicaset status, shard status, etc. You can provide those parameters with
    the environment variables `MONGOS_USER` and `MONGOS_PASSWORD`
    """

    short_desc = "Charmed Mongos"
    plugin_name = "charmed_mongos"

    # Triggers
    packages = ("charmed-mongodb",)
    containers = ("mongos",)

    snap_package = "charmed-mongodb"
    snap_path_common = "/var/snap/charmed-mongodb/common"
    snap_path_current = "/var/snap/charmed-mongodb/current"

    kube_cmd = "kubectl"
    selector = "app.kubernetes.io/name=mongos-k8s"

    conf_paths = {
        "MONGODB_CONF": "/etc/mongod",
        "MONGODB_LOGS": "/var/log/mongodb",
    }

    option_list = [
        PluginOpt(
            name="dumpdbs",
            default=False,
            val_type=bool,
            desc="Set to true to dump server information.",
        ),
        PluginOpt(
            "dbuser",
            default="",
            val_type=str,
            desc="Username for database dump collection",
        ),
        PluginOpt(
            "dbpass",
            default="",
            val_type=str,
            desc="Password for database dump collection",
        ),
    ]

    mongos_commands: Tuple[Tuple[str, str], ...] = (
        ("EJSON.stringify(db.serverStatus())", "server_status.txt"),
        ("EJSON.stringify(db.getUsers())", "db_users.txt"),
        ("EJSON.stringify(db.getRoles())", "db_roles.txt"),
        (
            "EJSON.stringify(db.adminCommand({listDatabases: 1}))",
            "db_databases.txt",
        ),
        ("EJSON.stringify(sh.status())", "shard_cluster_status.txt"),
        ("EJSON.stringify(sh.listShards())", "shard_shards.txt"),
    )

    def _join_conf_path(self, base: str, *parts: str):
        stripped_parts = [p.lstrip(os.path.sep) for p in parts]
        return self.path_join(base, *stripped_parts)

    def _get_db_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        db_user = self.get_option("dbuser")
        db_pass = self.get_option("dbpass")

        if not db_user:
            if "MONGOS_USER" in os.environ:
                self.soslog.info(
                    "MONGOS_USER present: Using MONGOS_USER environment"
                    "variable, user did not provide username."
                )
                db_user = os.environ["MONGOS_USER"]
            else:
                self.soslog.warning("error: Missing credentials (username)")
                return None, None

        if not db_pass:
            if "MONGOS_PWD" in os.environ:
                self.soslog.info(
                    "MONGOS_PWD present: Using MONGOS_PWD environment "
                    "variable, user did not provide password."
                )
                db_pass = os.environ["MONGOS_PWD"]
            else:
                self.soslog.warning("error: Missing credentials (password)")
                return None, None

        return db_user, db_pass

    def vm_config_db(self) -> Optional[str]:
        _conf_file = f"{self.conf_paths['MONGODB_CONF']}/mongos.conf"
        conf_path = self._join_conf_path(self.snap_path_current, _conf_file)
        try:
            with open(conf_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return data.get("sharding", {}).get("configDB", None)
        except FileNotFoundError:
            return None

    def k8s_config_db(
        self, kube_cmd: str, cont: str, pod: str
    ) -> Optional[str]:
        # Cat the configuration file.
        cat_conf_cmd = (
            f"{kube_cmd} exec -c {cont} {pod} -- "
            f"cat {self.conf_paths['MONGODB_CONF']}/mongos.conf"
        )
        result = self.exec_cmd(cat_conf_cmd)

        if result.get("status") != 0:
            return None

        data = yaml.safe_load(result.get("output", ""))
        return data.get("sharding", {}).get("configDB", None)

    def _process_snap(self):
        config_db = self.vm_config_db()

        if not config_db:
            # The service is not properly set up by the charm, exiting.
            return

        base_conf = self._join_conf_path(
            self.snap_path_current, self.conf_paths["MONGODB_CONF"]
        )
        base_logs = self._join_conf_path(
            self.snap_path_common, self.conf_paths["MONGODB_LOGS"]
        )

        all_logs = self.get_option("all_logs")

        # Hide certificates and cluster keyfile.
        self.add_forbidden_path(
            [
                f"{base_conf}/*.pem",
                f"{base_conf}/*.crt",
                f"{base_conf}/keyFile",
                f"{base_conf}/mongod.conf",
            ]
        )
        self.add_copy_spec([base_conf])

        if all_logs:
            self.add_copy_spec([f"{base_logs}/*"])
        else:
            self.add_copy_spec([f"{base_logs}/*.log"])

        lines = None if all_logs else 500
        self.add_journal("snap.charmed-mongodb.mongos", lines=lines)

        self.add_cmd_output("snap info charmed-mongodb")

        if not self.get_option("dumpdbs"):
            return

        db_user, db_pass = self._get_db_credentials()
        if not db_user or not db_pass:
            return

        mongos_uri = self._build_uri(db_user, Substrate.VM)
        mongodb_cmd = "charmed-mongodb.mongosh"
        env = {"MONGOS_PWD": db_pass}

        # --- REGULAR INFORMATION ---
        for command, suggest_filename in self.mongos_commands:
            self.add_cmd_output(
                (
                    f"sh -c '{mongodb_cmd} {mongos_uri} "
                    f"--quiet --eval \"{command}\"'"
                ),
                suggest_filename=suggest_filename,
                env=env,
            )

    def _build_uri(
        self,
        db_user: str,
        substrate: Substrate,
    ) -> str:
        base_conf = self.conf_paths["MONGODB_CONF"]
        args: Dict[str, str] = {"authSource": "admin"}

        if substrate == Substrate.VM:
            base_conf = self._join_conf_path(self.snap_path_current, base_conf)

        external_ca = Path(f"{base_conf}/external-ca.crt")
        external_cert = Path(f"{base_conf}/external-cert.pem")
        if external_ca.exists() and external_cert.exists():
            args |= {
                "tls": "true",
                "tlsCertificateKeyFile": f"{external_cert}",
                "tlsCaFile": f"{external_ca}",
            }
        _args = urlencode(args)
        user = quote_plus(db_user)
        host = "127.0.0.1:27018"
        socket_path = Path(f"{self.snap_path_current}/var/mongodb-27018.sock")
        if substrate == Substrate.VM and socket_path.exists():
            host = quote(f"{socket_path}", safe="")
        return f"mongodb://{user}:${{MONGOS_PWD}}@{host}/admin?{_args}"

    def _determine_namespaces(self) -> list[str]:
        namespaces = self.exec_cmd(
            f"{self.kube_cmd} get pods -A -l {self.selector} "
            "-o jsonpath='{.items[*].metadata.namespace}'"
        )
        if namespaces["status"] == 0:
            return list(set(namespaces["output"].strip().split()))
        return []

    def _get_pod_names(self, namespace) -> list[str]:
        pods = self.exec_cmd(
            f"{self.kube_cmd} -n {namespace} get pods -l {self.selector} "
            "-o jsonpath='{.items[*].metadata.name}'"
        )
        if pods["status"] == 0:
            return pods["output"].strip().split()
        return []

    def _remote_exec(
        self,
        kube_cmd: str,
        cont: str,
        pod: str,
        mongod_cmd: str,
        uri: str,
        password: str,
        cmd: str,
        cmd_name: str,
    ):
        output_file = f"/tmp/eval_{cmd_name}"  # nosec: B108
        # We first execute the command and write into a file
        query_cmd = (
            f"{kube_cmd} exec -c {cont} {pod} -- "
            f'sh -lc \'export MONGOS_PWD="{password}"; {mongod_cmd} {uri} '
            f'--quiet --eval "{cmd}" > {output_file}\''
        )

        self.exec_cmd(query_cmd)

        # We then cat that file to have the command output.
        cat_cmd = (
            f"{kube_cmd} exec -c {cont} {pod} -- "
            f"sh -lc 'cat {output_file} && rm {output_file}'"
        )

        self.add_cmd_output(
            cmds=cat_cmd,
            suggest_filename=f"{pod}_{cmd_name}",
        )

    def _collect_per_namespace(self, ns: str, all_logs: bool):
        kube_cmd = f"{self.kube_cmd} -n {ns}"

        mongodb_cont = "mongod"
        pods = self._get_pod_names(ns)
        logs_path = self.conf_paths["MONGODB_LOGS"]
        conf_path = self.conf_paths["MONGODB_CONF"]

        # Get the config and logs from each pod
        dump_files_path = self.get_cmd_output_path()
        for path in self.conf_paths.values():
            for pod in pods:
                name_prefix = f"{dump_files_path}/pods/{pod}/{path}"
                os.makedirs(name_prefix, exist_ok=True)
                copy_cmd = (
                    f"{kube_cmd} cp -c {mongodb_cont} "
                    f"{pod}:{path} {name_prefix}"
                )
                self.exec_cmd(copy_cmd)

        for pod in pods:
            if all_logs:  # This is all_logs
                self.add_copy_spec([f"{dump_files_path}/{pod}/{logs_path}/*"])
            else:
                self.add_copy_spec(
                    [f"{dump_files_path}/{pod}/{logs_path}/*.log"]
                )

            self.add_forbidden_path(
                [
                    f"{dump_files_path}/pods/{pod}/{conf_path}/*.pem",
                    f"{dump_files_path}/pods/{pod}/{conf_path}/*.crt",
                    f"{dump_files_path}/pods/{pod}/{conf_path}/keyFile",
                    f"{dump_files_path}/pods/{pod}/{conf_path}/mongod.conf",
                ]
            )
            self.add_copy_spec([f"{dump_files_path}/pods/{pod}/{conf_path}"])

        if not self.get_option("dumpdbs"):
            return

        db_user, db_pass = self._get_db_credentials()
        if not db_user or not db_pass:
            return

        mongos_uri = self._build_uri(db_user, Substrate.K8S)
        mongodb_cmd = "mongosh"

        for pod in pods:
            config_db = self.k8s_config_db(kube_cmd, mongodb_cont, pod)
            if not config_db:
                continue
            for command, suggest_filename in self.mongos_commands:
                self._remote_exec(
                    kube_cmd=kube_cmd,
                    cont=mongodb_cont,
                    pod=pod,
                    mongod_cmd=mongodb_cmd,
                    uri=mongos_uri,
                    password=db_pass,
                    cmd=command,
                    cmd_name=suggest_filename,
                )

    def _process_k8s(self):
        all_logs = self.get_option("all_logs") or False
        namespaces = self._determine_namespaces()
        for namespace in namespaces:
            self._collect_per_namespace(namespace, all_logs)

    def setup(self) -> None:
        if self.is_installed(self.snap_package):
            self._process_snap()

        if is_executable(self.kube_cmd, self.sysroot):
            self._process_k8s()

    def postproc(self):
        if self.is_installed(self.snap_package):
            substrate = Substrate.VM
            if not self.vm_config_db():
                # Service was not properly set up.
                return
        else:
            substrate = Substrate.K8S

        base_conf = self.conf_paths["MONGODB_CONF"]
        if substrate == Substrate.VM:
            base_conf = self._join_conf_path(self.snap_path_current, base_conf)
        else:
            base_conf = f"{self.get_cmd_output_path()}/pods/*/{base_conf}"
            shutil.rmtree(
                f"{self.get_cmd_output_path()}/pods",
                ignore_errors=True
            )

        # --- SCRUB PASSWORDS ---
        self.do_path_regex_sub(
            f"{base_conf}/*",
            regexp=r'("queryPassword": ")[^"]*"',
            subst=r"\1*********",
        )
