# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

import glob
import json
import re
from datetime import datetime
from functools import cached_property
from typing import Optional

from sos.report.plugins import Plugin, UbuntuPlugin

PATHS = {
    "CONF": "/var/snap/charmed-kafka/current/etc/kafka",
    "LOGS": "/var/snap/charmed-kafka/common/var/log/kafka",
}

DATE_FORMAT = "%Y-%m-%d-%H"


class CharmedKafka(Plugin, UbuntuPlugin):
    short_desc = "Charmed Kafka"
    plugin_name = "charmed_kafka"
    packages = ("charmed-kafka",)

    @cached_property
    def bootstrap_server(self) -> Optional[str]:
        try:
            lines = []
            with open(
                    f"{PATHS['CONF']}/client.properties",
                    encoding="utf-8",
            ) as f:
                lines = f.readlines()

            for line in lines:
                if "bootstrap" in line:
                    # ensure using internal address if
                    # not set in client.properties
                    return re.sub(
                        r":(?!1)(\d+)", r":1\1",
                        line.split("=")[1]
                    )

            return None
        except FileNotFoundError:
            return None

    @cached_property
    def default_bin_args(self) -> str:
        if not self.bootstrap_server:
            return ""

        return (
            f"--bootstrap-server {self.bootstrap_server}"
            f" --command-config {PATHS['CONF']}/client.properties"
        )

    def setup(self):
        if not self.bootstrap_server:
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
                "snap logs -n all charmed-kafka.daemon",
                suggest_filename="snap_logs_charmed-kafka_daemon",
            )
        else:
            self.add_cmd_output(
                "snap logs -n 500 all charmed-kafka.daemon",
                suggest_filename="snap_logs_charmed-kafka_daemon",
            )

        # --- TOPICS ---

        self.add_cmd_output(
            f"charmed-kafka.topics --describe {self.default_bin_args}",
            env={"KAFKA_OPTS": ""},
            suggest_filename="kafka-topics",
        )

        # --- CONFIGS ---

        for entity in ["topics", "clients", "users", "brokers", "ips"]:
            self.add_cmd_output(
                (
                    "charmed-kafka.configs --describe --all "
                    f"--entity-type {entity} {self.default_bin_args}"
                ),
                env={"KAFKA_OPTS": ""},
                suggest_filename=f"kafka-configs-{entity}",
            )

        # --- ACLs ---

        self.add_cmd_output(
            f"charmed-kafka.acls --list {self.default_bin_args}",
            env={"KAFKA_OPTS": ""},
            suggest_filename="kafka-acls",
        )

        # --- JMX METRICS ---

        self.add_cmd_output(
            "curl localhost:9101/metrics",
            suggest_filename="jmx-metrics"
        )

    def collect(self):

        # --- LOG DIRS ---

        log_dirs_output = self.exec_cmd(
            f"charmed-kafka.log-dirs --describe {self.default_bin_args}",
            env={"KAFKA_OPTS": ""},
        )
        log_dirs = {}

        # output has leading non-json lines that need cleaning, e.g:

        # Querying brokers for log directories information
        # Received log directory information from brokers 100,101,102
        # {"brokers":[{"broker":100,"logDirs":...

        if log_dirs_output and log_dirs_output["status"] == 0:
            for line in log_dirs_output["output"].splitlines():
                try:
                    log_dirs = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        with self.collection_file("kafka-log-dirs") as f:
            f.write(json.dumps(log_dirs, indent=4))

        # --- TRANSACTIONS ---

        transactions_list = self.exec_cmd(
            f"charmed-kafka.transactions {self.default_bin_args} list",
            env={"KAFKA_OPTS": ""},
        )
        transactional_ids = []

        if transactions_list and transactions_list["status"] == 0:
            transactional_ids = transactions_list["output"].splitlines()[1:]

        transactions_outputs = []
        for transactional_id in transactional_ids:
            transactions_describe = self.exec_cmd(
                (
                    f"charmed-kafka.transactions {self.default_bin_args}",
                    f"describe --transactional-id {transactional_id}",
                ),
            )

            if transactions_describe and transactions_describe["status"] == 0:
                transactions_outputs.append(transactions_describe["output"])

        with self.collection_file("kafka-transactions") as f:
            f.write("\n".join(transactions_outputs))

    def postproc(self):
        if not self.bootstrap_server:
            # service not properly set-up by the charm, skip
            return

        # --- SCRUB PASSWORDS ---

        self.do_path_regex_sub(
            f"{PATHS['CONF']}/*",
            r'(password=")[^"]*',
            r"\1*********",
        )
