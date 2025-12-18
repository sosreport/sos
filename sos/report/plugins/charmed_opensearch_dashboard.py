# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

import re
import os
from sos.report.plugins import Plugin,PluginOpt, IndependentPlugin

class OpenSearch(Plugin, IndependentPlugin):
    short_desc = 'Charmed OpenSearch Dashboard'
    plugin_name = 'charmed_opensearch_dashboard'
    option_list = [
        PluginOpt(
            "user", default="admin", val_type=str,
            desc="Username for opensearch, to check APIs"
        ),
        PluginOpt(
            "pass", default="", val_type=str,
            desc="Password for opensearch, to check APIs",
        ),
        PluginOpt(
            "all_log", default=True, val_type=bool,
            desc="Export all logs",
        )
    ]

    log_path = "/var/log/opensearch-dashboards"
    config_path = "/etc/opensearch-dashboards/opensearch_dashboards.yml"
    certificates_path = "/etc/opensearch-dashboards/certificates"
    node_config_path= "/etc/node.options"

    snap_current_path = "/var/snap/opensearch-dashboards/current"
    snap_common_path = "/var/snap/opensearch-dashboards/common"

    user,password = None, None

    def setup(self):
        self.user, self.password = self.get_credentials()
        if self.check_vm():
            self.export_vm()

    def check_vm(self):
        return os.path.exists(self.snap_common_path)

    def export_vm(self):
        opensearch_dashboard_config_file = f"{self.snap_current_path}{self.config_path}"
        self.add_copy_spec(opensearch_dashboard_config_file)

        if self.get_option("all_log"):
            self.add_copy_spec(f"{self.snap_common_path}{self.log_path}/*")
            self.add_copy_spec("/var/log/juju/*")
        else:
            self.add_copy_spec(f"{self.snap_common_path}{self.log_path}/*.log")

        self.add_copy_spec("/etc/environment")
        self.add_copy_spec("/var/lib/juju/agents/unit-opensearch-dashboards-*/charm/manifest.yaml")

        host, port = self.get_hostname_port(opensearch_dashboard_config_file)
        base_url = f"http://{host}:{port}"
        self.export_commands(base_url)

    def get_hostname_port(self, opensearch_config_file):
        """ Get hostname and port number """
        hostname = "localhost"
        port = "5601"

        try:
            with open(opensearch_config_file, encoding='UTF-8') as config:
                for line in config:
                    network_host = re.search(r'(^server.host):(.*)', line)
                    network_port = re.search(r'(^server.port):(.*)', line)
                    if network_host and len(network_host.groups()) == 2:
                        hostname = network_host.groups()[-1].strip()
                        hostname = re.sub(r'"|\'', '', hostname)
                        continue
                    if network_port and len(network_port.groups()) == 2:
                        port = network_port.groups()[-1].strip()
        except Exception as err:  # pylint: disable=broad-except
            self._log_info(f"Failed to parse {opensearch_config_file}: {err}")
        return hostname, port

    def get_credentials(self):
        user = self.get_option("user")
        password = self.get_option("pass")
        return user, password

    def export_commands(self, base_url):
        self.add_cmd_output(f"ls -la {self.snap_current_path}{self.certificates_path}",suggest_filename="certificates_paths")
        self.add_cmd_output("systemctl cat snap.opensearch-dashboards.exporter-daemon.service",suggest_filename="dashboard_exporter_service")
        self.add_cmd_output("systemctl cat snap.opensearch-dashboards.opensearch-dashboards-daemon.service",suggest_filename="dashboard_opensearch_service")
        self.add_cmd_output("snap get opensearch-dashboards -d", suggest_filename="snap_get_opensearch_dashboard")
        self.add_cmd_output("ps eww -fC node", suggest_filename="running_arguments")
        self.add_cmd_output("journalctl -u snap.opensearch-dashboards.* --no-pager -n 1000", suggest_filename="journal")
        self.add_cmd_output("ss -tulpn", suggest_filename="listening_ports")
        self.add_cmd_output("ps aux", suggest_filename="process_tree")

        base_cmd = f"curl -k -u {self.user}:{self.password} -X GET"
        self.add_cmd_output(f"{base_cmd} '{base_url}/api/status'", suggest_filename="status")
        self.add_cmd_output(f"{base_cmd} '{base_url}/api/stats?extended=true'", suggest_filename="stats")
        query = "type=dashboard&type=visualization&type=index-pattern&type=search&per_page=1&fields=id"
        self.add_cmd_output(f"{base_cmd} '{base_url}/api/saved_objects/_find?{query}'", suggest_filename="saved_object_count")




# sudo sos report -o charmed_opensearch_dashboard charmed_opensearch_dashboard.pass=5OhVLjyLNd70IfBomZlIeYQxHc9izYmu -k charmed_opensearch_dashboard.all-log=on
