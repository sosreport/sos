# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#
import os

import yaml

from sos.report.plugins import Plugin, PluginOpt, UbuntuPlugin


class CharmedOpenSearch(Plugin, UbuntuPlugin):
    short_desc = 'Charmed OpenSearch'
    plugin_name = 'charmed_opensearch'
    option_list = [
        PluginOpt(
            "user", default="admin", val_type=str,
            desc="Username for opensearch, to check APIs"
        ),
        PluginOpt(
            "password", default="", val_type=str,
            desc="Password for opensearch, to check APIs",
        ),
        PluginOpt(
            "all_journal", default=False, val_type=bool,
            desc="Export all the journal entries",
        )
    ]

    log_path = "/var/log/opensearch"
    etc_path = "/etc/opensearch"
    certificates_path = f"{etc_path}/certificates"
    config_path = f"{etc_path}/opensearch.yml"
    snap_current_path = "/var/snap/opensearch/current"
    snap_common_path = "/var/snap/opensearch/common"
    hostname = "localhost"
    port = "9200"
    packages = ('opensearch',)
    services = ('jujud-machine-*.service',)

    def setup(self):
        opensearch_config_directory = (f"{self.snap_current_path}"
                                       f"{self.etc_path}")
        # FORBIDDEN
        self.add_forbidden_path([
            f"{opensearch_config_directory}/certificates",
            f"{opensearch_config_directory}/opensearch.keystore",
        ])

        # CONFIGS
        self.add_copy_spec(f"{opensearch_config_directory}/*")

        # CERTIFICATES
        self.add_dir_listing(
            f"{self.snap_current_path}{self.certificates_path}",
            suggest_filename="certificates_paths"
        )

        # JOURNAL
        if self.get_option("all_journal"):
            self.add_journal(units="snap.opensearch.*", allfields=True)
        else:
            self.add_journal(units="snap.opensearch.*", lines=1000,
                             allfields=True)

        # LOGS
        if self.get_option("all_logs"):
            self.add_copy_spec(f"{self.snap_common_path}{self.log_path}/*")
        else:
            self.add_copy_spec(f"{self.snap_common_path}{self.log_path}/*.log")

        # SNAP
        self.add_cmd_output(
            "snap get opensearch -d",
            suggest_filename="snap_get_opensearch"
        )

        # API
        self.get_hostname_port(f"{self.snap_current_path}{self.config_path}")
        base_url = f"https://{self.hostname}:{self.port}"
        self.export_api(base_url)

    def get_hostname_port(self, opensearch_config_file):
        """ Get hostname and port number parsing as YAML """
        try:
            with open(opensearch_config_file, 'r', encoding='UTF-8') as f:
                config = yaml.safe_load(f) or {}
            if config.get('network.publish_host'):
                self.hostname = str(config.get('network.publish_host'))
            if config.get('http.port'):
                self.port = str(config.get('http.port'))
        except Exception as err:  # pylint: disable=broad-except
            self._log_info(f"Failed to parse {opensearch_config_file}: {err}")

    def export_api(self, base_url):
        temp_env = os.environ.copy()
        if not os.environ.get("OPENSEARCH_PWD"):
            if not self.get_option('password'):
                self.soslog.warning(
                    "dump_error: password are not provided,"
                    " skipping API dumps."
                )
                return
            temp_env["OPENSEARCH_PWD"] = self.get_option('password')

        if not os.environ.get("OPENSEARCH_USER"):
            temp_env["OPENSEARCH_USER"] = self.get_option('user')

        cluster_collect = [
            "stats",
            "settings",
            "health",
        ]
        for collect in cluster_collect:
            self.add_cmd_output(
                f"sh -c 'curl -k -u $OPENSEARCH_USER:$OPENSEARCH_PWD "
                f"-X GET {base_url}/_cluster/{collect}?pretty'",
                suggest_filename=collect,
                env=temp_env
            )
        cat_collect = [
            "nodes?v",
            "indices",
            "shards",
            "aliases",
        ]
        for collect in cat_collect:
            self.add_cmd_output(
                f"sh -c 'curl -k -u $OPENSEARCH_USER:$OPENSEARCH_PWD "
                f"-X GET {base_url}/_cat/{collect}'",
                suggest_filename=collect,
                env=temp_env
            )

    def postproc(self):
        # SCRUB PASSWORDS
        opensearch_config_file = (f"{self.snap_current_path}"
                                  f"{self.config_path}")
        self.do_path_regex_sub(
            f"{opensearch_config_file}",
            r"(\s*plugins\.security\.ssl\..+password\s*:\s+).*",
            r'\1"*********"',
        )
