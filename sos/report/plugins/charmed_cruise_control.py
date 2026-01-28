# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

import glob
import re
from datetime import datetime
from functools import cached_property

from sos.report.plugins import Plugin, UbuntuPlugin

PATHS = {
    "CONF": "/var/snap/charmed-kafka/current/etc/cruise-control",
    "LOGS": "/var/snap/charmed-kafka/common/var/log/cruise-control",
}

DATE_FORMAT = "%Y-%m-%d-%H"


class CharmedCruiseControl(Plugin, UbuntuPlugin):
    short_desc = "Cruise Control (from Charmed Kafka)"
    plugin_name = "charmed_cruise_control"
    packages = ("charmed-kafka",)

    @cached_property
    def credentials_args(self) -> str:
        with open(
            f"{PATHS['CONF']}/cruisecontrol.credentials",
            encoding="utf-8",
        ) as f:
            content = f.read().strip()

        if match := re.match(r"balancer: (?P<pwd>\w+),ADMIN", content):
            pwd = match.group("pwd")
            return f"-u balancer:{pwd}"

        return ""

    def setup(self):
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

        # --- SNAP LOGS ---

        if all_logs:
            self.add_cmd_output(
                "snap logs charmed-kafka.cruise-control",
                suggest_filename="snap_logs_charmed-kafka_cruise-control",
            )
        else:
            self.add_cmd_output(
                "snap logs charmed-kafka.cruise-control -n 10000",
                suggest_filename="snap_logs_charmed-kafka_cruise-control",
            )

        # --- CRUISE CONTROL STATE ---

        self.add_cmd_output(
            f"curl {self.credentials_args} localhost:9090/kafkacruisecontrol/state?super_verbose=true",  # noqa: E501 # pylint:disable=line-too-long
            "cruise-control-state",
        )

        # --- CLUSTER STATE ---

        self.add_cmd_output(
            f"curl {self.credentials_args} localhost:9090/kafkacruisecontrol/kafka_cluster_state?verbose=true",  # noqa: E501 # pylint:disable=line-too-long
            "cluster-state",
        )

        # --- PARTITION LOAD ---

        self.add_cmd_output(
            f"curl {self.credentials_args} localhost:9090/kafkacruisecontrol/partition_load",  # noqa: E501 # pylint:disable=line-too-long
            "partition-load",
        )

        # --- USER TASKS ---

        self.add_cmd_output(
            f"curl {self.credentials_args} localhost:9090/kafkacruisecontrol/user_tasks",  # noqa: E501 # pylint:disable=line-too-long
            "user-tasks",
        )

        # --- JMX METRICS ---

        self.add_cmd_output("curl localhost:9102/metrics", "jmx-metrics")

    def postproc(self):
        # --- SCRUB PASSWORDS ---

        for scrub_pattern in [r'(password=")[^"]*', r"(balancer: )[^,]*"]:
            self.do_path_regex_sub(
                f"{PATHS['CONF']}/*",
                scrub_pattern,
                r"\1*********",
            )
