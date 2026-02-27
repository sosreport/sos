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


class OpenSearchDashboards(Plugin, UbuntuPlugin):
    short_desc = "Charmed OpenSearch Dashboards"
    plugin_name = "charmed_opensearch_dashboards"
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

    log_path = "/var/log/opensearch-dashboards"
    etc_path = "/etc/opensearch-dashboards"
    config_path = f"{etc_path}/opensearch_dashboards.yml"
    certificates_path = f"{etc_path}/certificates"
    node_config_path = f"{etc_path}/node.options"
    snap_current_path = "/var/snap/opensearch-dashboards/current"
    snap_common_path = "/var/snap/opensearch-dashboards/common"
    hostname = "localhost"
    port = "5601"
    packages = ('opensearch-dashboards',)

    def setup(self):
        # CONFIGS
        opensearch_dashboard_config_file = \
            f"{self.snap_current_path}{self.config_path}"

        self.add_copy_spec(opensearch_dashboard_config_file)
        self.add_copy_spec(
            f"{self.snap_current_path}{self.node_config_path}")

        # LOGS
        if self.get_option("all_logs"):
            self.add_copy_spec(f"{self.snap_common_path}{self.log_path}/*")
        else:
            self.add_copy_spec(
                f"{self.snap_common_path}{self.log_path}/*.log")

        # JOURNAL
        if self.get_option("all_journal"):
            self.add_journal(units="snap.opensearch-dashboards.*",
                             allfields=True)
        else:
            self.add_journal(units="snap.opensearch-dashboards.*", lines=1000,
                             allfields=True)

        # SNAP
        self.add_cmd_output(
            "snap get opensearch-dashboards -d",
            suggest_filename="snap_get_opensearch_dashboard"
        )

        # CERTIFICATES
        self.add_dir_listing(
            f"{self.snap_current_path}{self.certificates_path}",
            suggest_filename="certificates_paths"
        )

        # API
        self.get_hostname_port(opensearch_dashboard_config_file)
        base_url = f"https://{self.hostname}:{self.port}"
        self.export_api(base_url)

    def get_hostname_port(self, opensearch_config_file):
        """ Get hostname and port number parsing as YAML """
        try:
            with open(opensearch_config_file, 'r', encoding='UTF-8') as f:
                config = yaml.safe_load(f) or {}

            if config.get('server.host'):
                self.hostname = str(config.get('server.host'))

            if config.get('server.port'):
                self.port = str(config.get('server.port'))

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

        query = ("type=dashboard&"
                 "type=visualization&"
                 "type=index-pattern&"
                 "type=search&per_page=1&"
                 "fields=id")

        self.add_cmd_output(
            f"sh -c 'curl -k -u $OPENSEARCH_USER:$OPENSEARCH_PWD "
            f"-X GET {base_url}/api/settings'",
            suggest_filename="settings",
            env=temp_env)
        self.add_cmd_output(
            f"sh -c 'curl -k -u $OPENSEARCH_USER:$OPENSEARCH_PWD "
            f"-X GET {base_url}/api/stats?extended=true'",
            suggest_filename="stats",
            env=temp_env)
        self.add_cmd_output(
            f"sh -c 'curl -k -u $OPENSEARCH_USER:$OPENSEARCH_PWD "
            f"-X GET {base_url}/api/saved_objects/_find?{query}'",
            suggest_filename="saved_object_count",
            env=temp_env)

    def postproc(self):
        # SCRUB PASSWORDS
        opensearch_dashboard_config_file = (f"{self.snap_current_path}"
                                            f"{self.config_path}")
        self.do_path_regex_sub(
            f"{opensearch_dashboard_config_file}",
            r"(\s*opensearch\.password\s*:\s+).*",
            r'\1"*********"',
        )
