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
        try:
            with open(
                f"{PATHS['CONF']}/cruisecontrol.credentials",
                encoding="utf-8",
            ) as f:
                content = f.read().strip()

            if match := re.match(r"balancer: (?P<pwd>\w+),ADMIN", content):
                pwd = match.group("pwd")
                return f"-u balancer:{pwd}"

            return ""
        except FileNotFoundError:
            return ""

    def setup(self):
        if not self.credentials_args:
            # service not properly set-up, skip
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
                "snap logs -n all charmed-kafka.cruise-control",
                suggest_filename="snap_logs_charmed-kafka_cruise-control",
            )
        else:
            self.add_cmd_output(
                "snap logs -n 500 charmed-kafka.cruise-control",
                suggest_filename="snap_logs_charmed-kafka_cruise-control",
            )

        # --- STATE, TASKS, PARTITION LOAD ---

        endpoints = {
            'cruise-control-state': 'state?super_verbose=true',
            'cluster-state': 'kafka_cluster_state?verbose=true',
            'partition_load': 'partition_load',
            'user-tasks': 'user_tasks',
        }

        url = 'localhost:9090/kafkacruisecontrol'

        for fname, api in endpoints.items():
            self.add_cmd_output(
                f"curl {self.credentials_args} {url}/{api}",
                suggest_filename=fname,
            )

        # --- JMX METRICS ---

        self.add_cmd_output(
            "curl localhost:9102/metrics",
            suggest_filename="jmx-metrics"
        )

    def postproc(self):
        if not self.credentials_args:
            # service not properly set-up, skip
            return

        # --- SCRUB PASSWORDS ---

        for scrub_pattern in [r'(password=")[^"]*', r"(balancer: )[^,]*"]:
            self.do_path_regex_sub(
                f"{PATHS['CONF']}/*",
                scrub_pattern,
                r"\1*********",
            )
