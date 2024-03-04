from datetime import datetime, timedelta
from sos.report.plugins import Plugin, UbuntuPlugin, PluginOpt
import glob
import re
import os
import json

PATHS = {
    "CONF": "/var/snap/charmed-zookeeper/current/etc/zookeeper",
    "LOGS": "/var/snap/charmed-zookeeper/common/var/log/zookeeper",
    "DATA-LOG": "/var/snap/charmed-zookeeper/common/var/lib/zookeeper/data-log",
    "DATA": "/var/snap/charmed-zookeeper/common/var/lib/zookeeper/data",
    "BIN": "/snap/charmed-zookeeper/current/opt/zookeeper/bin",
    "JRE": "/snap/charmed-zookeeper/current/usr/lib/jvm/java-8-openjdk-amd64/jre",
}

DATE_FORMAT = "%Y-%m-%d-%H"
TEMP_JAAS = "client.jaas"


class CharmedZooKeeper(Plugin, UbuntuPlugin):

    short_desc = "Charmed ZooKeeper"
    plugin_name = "charmed_zookeeper"

    current_date = datetime.now()
    default_date_from = "1970-01-01-00"
    default_date_to = (current_date + timedelta(hours=1)).strftime(DATE_FORMAT)

    option_list = [
        PluginOpt(
            "date-from",
            default="1970-01-01-00",
            desc="date from which to filter logs, in format YYYY-MM-DD-HH",
            val_type=str,
        ),
        PluginOpt(
            "date-to",
            default=default_date_to,
            desc="date to which to filter logs, in format YYYY-MM-DD-HH",
            val_type=str,
        ),
    ]

    @property
    def default_env(self) -> dict[str, str]:
        return {
            "JAVA_HOME": PATHS["JRE"],
            "CLIENT_JVMFLAGS": f"-Djava.security.auth.login.config={PATHS['CONF']}/{TEMP_JAAS}",
            "SERVER_JVMFLAGS": "",
        }

    @property
    def super_password(self) -> str | None:
        with open(f"{PATHS['CONF']}/{TEMP_JAAS}", "r") as f:
            for line in f.readlines():
                if "super" in line:
                    return line.split("=")[1].replace(";", "").replace('"', "").strip()

        return ""

    def setup(self):
        # creating temporary jaas file for super user SASL auth
        with open(f"{PATHS['CONF']}/{TEMP_JAAS}", "w") as f:
            f.write(
                f"""
            Client {{
                org.apache.zookeeper.server.auth.DigestLoginModule required
                username="super"
                password="{self.super_password}";
            }};
                """
            )

        # --- FILE EXCLUSIONS ---

        for file in glob.glob(f"{PATHS['LOGS']}/*"):
            date = re.search(
                pattern=r"([0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2})", string=file
            )

            # include files without date, aka current files
            if not date:
                continue

            file_dt = datetime.strptime(date.group(1), DATE_FORMAT)

            if file_dt < datetime.strptime(
                str(self.get_option("date-from")), DATE_FORMAT
            ) or file_dt > datetime.strptime(
                str(self.get_option("date-to")), DATE_FORMAT
            ):
                # skip files outside given range
                self.add_forbidden_path(file)

        # hide keys/stores
        self.add_forbidden_path(
            [
                f"{PATHS['CONF']}/*.pem",
                f"{PATHS['CONF']}/*.p12",
                f"{PATHS['CONF']}/*.jks",
                f"{PATHS['CONF']}/{TEMP_JAAS}",
            ]
        )

        # --- FILE INCLUSIONS ---

        self.add_copy_spec(
            [
                f"{PATHS['CONF']}",
                f"{PATHS['LOGS']}",
                "/var/log/juju",
            ]
        )

        # --- SNAP LOGS ---

        self.add_cmd_output(
            "snap logs charmed-zookeeper.daemon -n 100000", suggest_filename="snap-logs"
        )

        # --- TRANSACTIONS ---

        for file in glob.glob(f"{PATHS['DATA-LOG']}/version-2/*"):
            transactions = self.exec_cmd(
                f"{PATHS['BIN']}/zkTxnLogToolkit.sh -d {file}",
                env=self.default_env,
            )

            if not (transactions and transactions["status"] == 0):
                continue

            valid_dt_transactions = []
            for transaction in transactions["output"].splitlines():
                try:
                    log_dt = datetime.strptime(
                        " ".join(transaction.split()[:4]), "%m/%d/%y %I:%M:%S %p %Z"
                    )
                except ValueError:  # must've been a bad line
                    continue

                if log_dt < datetime.strptime(
                    str(self.get_option("date-from")), DATE_FORMAT
                ) or log_dt > datetime.strptime(
                    str(self.get_option("date-to")), DATE_FORMAT
                ):
                    continue

                valid_dt_transactions.append(transaction)

            with self.collection_file(
                f"zookeeper-transaction-{os.path.basename(file)}"
            ) as f:
                f.write("\n".join(valid_dt_transactions))

        # --- SNAPSHOT ---

        most_recent_file = sorted(glob.glob(f"{PATHS['DATA']}/version-2/*"))[-1]

        snapshot_json = self.exec_cmd(
            f"{PATHS['BIN']}/zkSnapShotToolkit.sh -json {most_recent_file}",
            env=self.default_env,
        )
        snapshot = {}

        if snapshot_json and snapshot_json["status"] == 0:
            for line in snapshot_json["output"].splitlines():
                try:
                    snapshot = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        with self.collection_file("zookeeper-snapshot") as f:
            f.write(json.dumps(snapshot, indent=4))

        # --- JMX METRICS ---

        self.add_cmd_output("curl localhost:9998/metrics", "jmx-metrics")

        # --- PROVIDER METRICS ---

        self.add_cmd_output("curl localhost:7000/metrics", "provider-metrics")

    def postproc(self):
        # --- SCRUB PASSWORDS ---

        self.do_path_regex_sub(
            f"{PATHS['CONF']}/*",
            r'(password=")[^"]*',
            r"\1*********",
        )

        os.remove(f"{PATHS['CONF']}/{TEMP_JAAS}")
