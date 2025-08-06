# Copyright (C) 2025 Canonical Ltd.,
#                    Mateusz Kulewicz <mateusz.kulewicz@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from typing import Optional
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError, dumps, loads
from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Loki(Plugin, IndependentPlugin):
    """
    Collects logs and configuration from Loki.

    This plugin interacts with the Loki API to fetch logs based on specified
    labels and provides options for pagination and label detection.
    It also collects relevant configuration files and masks sensitive
    information. It works with both charmed and non-charmed Loki.
    To fetch internal Loki logs, run it from the Loki container.
    You can also run it from another machine and fetch only logs from
    Loki API, by providing the following parameters:
        `-k loki.collect-logs=true -k loki.endpoint=LOKI_URL`

    Usage:
        sos report -o loki -k loki.collect-logs=true \
            -k loki.labels=severity:charm -k loki.detect-labels=true \
            -k loki.paginate=true -k loki.endpoint=LOKI_URL
    """

    short_desc = 'Loki service'
    plugin_name = 'loki'
    profiles = ('services', )
    LOKI_QUERY_LIMIT = 5000
    MAX_PAGINATION_ITERATIONS = 100

    packages = ('loki', )

    option_list = [
        PluginOpt('collect-logs', default=False,
                  desc='collect logs from Loki API'),
        PluginOpt('detect-labels', default=False,
                  desc=('fetch logs for all available labels. '
                        'May result in multiple files with the same logs')),
        PluginOpt('paginate', default=False,
                  desc='fetch all available logs from Loki API.'),
        PluginOpt('labels', default='', val_type=str,
                  desc='colon-delimited list of labels to fetch logs from'),
        PluginOpt('endpoint', default='http://localhost:3100', val_type=str,
                  desc=('loki endpoint to fetch logs from. '
                        'Defaults to http://localhost:3100.')),
    ]

    def query_command(self, endpoint, label, start: Optional[datetime],
                      end: Optional[datetime]):
        if not end:
            end = datetime.now(timezone.utc)
        if not start:
            start = end - timedelta(days=1)

        start_formatted = start.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        end_formatted = end.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        command = (
            f"curl -G -s '{endpoint}/loki/api/v1/query_range' "
            f"--data-urlencode 'query={{{label}=~\".+\"}}' "
            f"--data-urlencode 'start={start_formatted}' "
            f"--data-urlencode 'end={end_formatted}' "
            f"--data-urlencode 'limit={Loki.LOKI_QUERY_LIMIT}' "
        )
        return command

    def get_logs(self, endpoint, label, start: Optional[datetime],
                 end: Optional[datetime]):
        output = self.exec_cmd(self.query_command(endpoint, label, start, end))
        try:
            return loads(output["output"])
        except JSONDecodeError:
            # if an error is returned from Loki API, the output will be str
            self._log_warn((f"An error was returned from Loki API on label "
                            f"{label}. "
                            f"Error message stored, not querying further."))
            return output["output"]

    def get_earliest_log_timestamp(self, logs):
        log_streams = logs["data"]["result"]
        # use now as a comparison
        earliest_log = int(datetime.now().timestamp()*1_000_000_000)
        for stream in log_streams:
            for log in stream["values"]:
                timestamp = int(log[0])
                earliest_log = min(earliest_log, timestamp)
        return earliest_log

    def get_logs_for_label(self, endpoint, label, paginate):
        logs = self.get_logs(endpoint, label, None, None)
        with self.collection_file(f'{label}.log') as logfile:
            logfile.write(dumps(logs, indent=2))
        if isinstance(logs, str):
            # don't paginate if error was returned
            return

        if paginate:
            earliest_log = self.get_earliest_log_timestamp(logs)
            previous_earliest_log = int(
                datetime.now().timestamp()*1_000_000_000
            )
            iterations_count = 0
            while iterations_count < Loki.MAX_PAGINATION_ITERATIONS and \
                    earliest_log < previous_earliest_log:
                log_timestamp = datetime.fromtimestamp(
                                    earliest_log / 1_000_000_000)
                new_logs = self.get_logs(endpoint, label, None, log_timestamp)
                with self.collection_file(f'{label}.log.{iterations_count}') \
                        as logfile:
                    logfile.write(dumps(new_logs, indent=2))
                if isinstance(new_logs, str):
                    # don't paginate further if error was returned
                    return
                previous_earliest_log = earliest_log
                earliest_log = \
                    self.get_earliest_log_timestamp(new_logs)
                # exit at most after 100 pages to avoid infinite loops
                iterations_count += 1

    def setup(self):
        els_config_file = self.path_join("/etc/loki/*.yaml")
        self.add_copy_spec(els_config_file)

        # charms using cos-coordinated-workers have their config elsewhere
        coordinated_workers_config_file = self.path_join("/etc/worker/*.yaml")
        self.add_copy_spec(coordinated_workers_config_file)

        self.add_copy_spec("/var/log/loki/*")
        self.add_cmd_output("pebble logs loki -n 10000")

        if self.get_option("collect-logs"):
            endpoint = self.get_option("endpoint") or "http://localhost:3100"
            self.labels = []
            if labels_option := self.get_option("labels"):
                if isinstance(labels_option, str) and labels_option:
                    self.labels.extend(labels_option.split(":"))

            if self.get_option("detect-labels"):
                labels_cmd = self.collect_cmd_output(
                    f"curl -G -s '{endpoint}/loki/api/v1/labels'"
                )
                labels_json = loads(labels_cmd["output"])
                self.labels.extend(labels_json["data"])

    def collect(self):
        endpoint = self.get_option("endpoint") or "http://localhost:3100"
        for label in self.labels:
            paginate = self.get_option("paginate")
            self.get_logs_for_label(endpoint, label, paginate)

    def postproc(self):
        protect_keys = [
            "access_key_id",
            "secret_access_key",
        ]
        loki_files = [
            "/etc/loki/loki-local-config.yaml",
            "/etc/loki/config.yaml",
            "/etc/loki/local-config.yaml",
            "/etc/loki/loki.yaml",
            "/etc/worker/config.yaml",
        ]

        match_exp_multil = fr"({'|'.join(protect_keys)})\s*(:|=)(\S*\n.*?\\n)"
        match_exp = fr"({'|'.join(protect_keys)})\s*(:|=)\s*[a-zA-Z0-9]*"

        for file in loki_files:
            self.do_file_sub(
                file, match_exp_multil,
                r"\1\2*********"
            )
            self.do_file_sub(
                file, match_exp,
                r"\1\2*********"
            )

# vim: set et ts=4 sw=4 :
