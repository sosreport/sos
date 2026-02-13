# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

import glob
import json
import os
import re
from datetime import datetime
from functools import cached_property

from sos.report.plugins import Plugin, UbuntuPlugin

PATHS = {
    "CONF": "/var/snap/charmed-zookeeper/current/etc/zookeeper",
    "LOGS": "/var/snap/charmed-zookeeper/common/var/log/zookeeper",
    "DATA-LOG": "/var/snap/charmed-zookeeper/common/var/lib/zookeeper/data-log",  # noqa: E501 # pylint:disable=line-too-long
    "DATA": "/var/snap/charmed-zookeeper/common/var/lib/zookeeper/data",
    "BIN": "/snap/charmed-zookeeper/current/opt/zookeeper/bin",
    "JRE": "/snap/charmed-zookeeper/current/usr/lib/jvm/java-11-openjdk-amd64/jre",  # noqa: E501 # pylint:disable=line-too-long
}

DATE_FORMAT = "%Y-%m-%d-%H"
CLIENT_JAAS = "client-jaas.cfg"


class CharmedZooKeeper(Plugin, UbuntuPlugin):
    short_desc = "Charmed ZooKeeper"
    plugin_name = "charmed_zookeeper"
    packages = ("charmed-zookeeper",)

    default_env = {
            "JAVA_HOME": PATHS["JRE"],
            "CLIENT_JVMFLAGS": f"-Djava.security.auth.login.config={PATHS['CONF']}/{CLIENT_JAAS}",  # noqa: E501 # pylint:disable=line-too-long
            "SERVER_JVMFLAGS": "",
    }

    @cached_property
    def super_password(self) -> str:
        try:
            with open(
                f"{PATHS['CONF']}/{CLIENT_JAAS}",
                "r",
                encoding="utf-8"
            ) as f:
                for line in f.readlines():
                    if "super" in line:
                        pw = line.split("=")[1].replace(";", "")
                        return pw.replace('"', "").strip()

            return ""
        except FileNotFoundError:
            return ""

    def setup(self):
        if not self.super_password:
            # service not properly set-up by the charm, skip
            return

        # --- FILE EXCLUSIONS ---

        all_logs = self.get_option("all_logs")
        since = self.get_option("since")

        for file in glob.glob(f"{PATHS['LOGS']}/*"):
            date = re.search(
                pattern=r"([0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2})", string=file
            )

            # include files without date, aka current files
            if not date:
                continue

            file_dt = datetime.strptime(date.group(1), DATE_FORMAT)

            if (
                since
                and not all_logs
                and file_dt < datetime.strptime(str(since), DATE_FORMAT)
            ):
                # skip files outside given range
                self.add_forbidden_path(file)

        # hide keys/stores
        self.add_forbidden_path([
                f"{PATHS['CONF']}/*.pem",
                f"{PATHS['CONF']}/*.key",
                f"{PATHS['CONF']}/*.p12",
                f"{PATHS['CONF']}/*.jks",
                f"{PATHS['CONF']}/{CLIENT_JAAS}",
        ])

        # --- FILE INCLUSIONS ---

        self.add_copy_spec(
            [
                f"{PATHS['CONF']}",
                f"{PATHS['LOGS']}",
            ]
        )

        # --- SNAP LOGS ---

        if all_logs:
            self.add_cmd_output(
                "snap logs -n all charmed-zookeeper.daemon",
                suggest_filename="snap_logs_charmed-zookeeper_daemon",
            )
        else:
            self.add_cmd_output(
                "snap logs -n 500 charmed-zookeeper.daemon",
                suggest_filename="snap_logs_charmed-zookeeper_daemon",
            )

        # --- JMX METRICS ---

        self.add_cmd_output(
            "curl localhost:9998/metrics",
            suggest_filename="jmx-metrics"
        )

        # --- PROVIDER METRICS ---

        self.add_cmd_output(
            "curl localhost:7000/metrics",
            suggest_filename="provider-metrics"
        )

    def collect(self):
        # --- TRANSACTIONS ---
        all_logs = self.get_option("all_logs")
        since = self.get_option("since")

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
                        " ".join(transaction.split()[:4]),
                        "%m/%d/%y %I:%M:%S %p %Z",
                    )
                except ValueError:  # must've been a bad line
                    continue

                if (
                    since
                    and not all_logs
                    and log_dt < datetime.strptime(str(since), DATE_FORMAT)
                ):
                    continue

                valid_dt_transactions.append(transaction)

            with self.collection_file(
                f"zookeeper-transaction-{os.path.basename(file)}"
            ) as f:
                f.write("\n".join(valid_dt_transactions))

        # --- SNAPSHOT ---
        files = glob.glob(f"{PATHS['DATA']}/version-2/*")
        if not files:
            return

        most_recent_file = sorted(files)[-1]
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

    def postproc(self):
        if not self.super_password:
            # service not properly set-up by the charm, skip
            return

        # --- SCRUB PASSWORDS ---

        self.do_path_regex_sub(
            f"{PATHS['CONF']}/*",
            r'(password=")[^"]*',
            r"\1*********",
        )
