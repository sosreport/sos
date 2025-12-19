# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

import re
import os

from sos.report.plugins import Plugin,PluginOpt, UbuntuPlugin

class OpenSearch(Plugin, UbuntuPlugin):
    short_desc = 'Charmed OpenSearch'
    plugin_name = 'charmed_opensearch'
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

    log_path = "/var/log/opensearch"
    etc_path = "/etc/opensearch"
    certificates_path = f"{etc_path}/certificates"
    config_path = f"{etc_path}/opensearch.yml"

    snap_current_path = "/var/snap/opensearch/current"
    snap_common_path = "/var/snap/opensearch/common"
    user,password = None, None

    def setup(self):
        self.user, self.password = self.get_credentials()
        if self.check_vm():
            self.export_vm()

    def check_vm(self):
        return os.path.exists(self.snap_current_path)

    def export_vm(self):
        opensearch_config_directory= f"{self.snap_current_path}{self.etc_path}"
        # FORBIDDEN
        self.add_forbidden_path([
            f"{opensearch_config_directory}/certificates",
            f"{opensearch_config_directory}/opensearch.keystore",
        ])

        # CONFIGS
        self.add_copy_spec(f"{opensearch_config_directory}/*")

        # CERTIFICATES
        # We don't export certificates, just paths
        self.add_cmd_output(
            f"ls -la {self.snap_current_path}{self.certificates_path}",
            suggest_filename="certificates_paths"
        )

        # JOURNAL
        self.add_journal(units="snap.opensearch.*", lines=1000, allfields=True)

        # SERVICES
        self.add_service_status("snap.opensearch.daemon",
                                suggest_filename="service_status_opensearch")
        self.add_cmd_output(
            "systemctl cat snap.opensearch.daemon.service",
            suggest_filename="service_cat_opensearch"
        )

        # LOGS
        if self.get_option("all_log"):
            self.add_copy_spec(f"{self.snap_common_path}{self.log_path}/*")
        else:
            self.add_copy_spec(f"{self.snap_common_path}{self.log_path}/*.log")

        # SNAP
        self.add_cmd_output(
            "snap get opensearch -d",
            suggest_filename="snap_get_opensearch"
        )

        # PORTS
        self.add_cmd_output(
            "sh -c \"ss -tulpn | awk 'NR==1 || /9200/'\"",
            suggest_filename="listening_ports"
        )

        # PROCESS TREE
        self.add_cmd_output(
            "sh -c \"ps aux | awk 'NR==1 || /opensearch/'\"",
            suggest_filename="process_tree"
        )

        # API
        host, port = self.get_hostname_port(f"{self.snap_current_path}{self.config_path}")
        base_url = f"https://{host}:{port}"
        self.export_api(base_url)

    def get_hostname_port(self, opensearch_config_file):
        """ Get hostname and port number """
        hostname = "localhost"
        port = "9200"

        try:
            with open(opensearch_config_file, encoding='UTF-8') as config:
                for line in config:
                    network_host = re.search(r'(^network.publish_host):(.*)', line)
                    network_port = re.search(r'(^http.port):(.*)', line)
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

    def export_api(self, base_url):
        base_cmd = f"curl -k -u {self.user}:{self.password} -X GET"
        self.add_cmd_output(f"{base_cmd} '{base_url}/_cluster/settings?pretty'", suggest_filename="settings")
        self.add_cmd_output(f"{base_cmd} '{base_url}/_cluster/health?pretty'", suggest_filename="health")
        self.add_cmd_output(f"{base_cmd} '{base_url}/_cluster/stats?pretty'", suggest_filename="stats")
        self.add_cmd_output(f"{base_cmd} '{base_url}/_cat/nodes?v'", suggest_filename="nodes")
        self.add_cmd_output(f"{base_cmd} '{base_url}/_cat/indices'", suggest_filename="indices")
        self.add_cmd_output(f"{base_cmd} '{base_url}/_cat/shards'", suggest_filename="shards")
        self.add_cmd_output(f"{base_cmd} '{base_url}/_cat/aliases'", suggest_filename="aliases")

    def postproc(self):
        # SCRUB PASSWORDS
        if self.check_vm():
            opensearch_config_file = f"{self.snap_current_path}{self.config_path}"
        else:
            opensearch_config_file = ""

        self.do_path_regex_sub(
            f"{opensearch_config_file}",
            r"(\s*plugins\.security\.ssl\..+password\s*:\s+).*",
            r'\1"*********"',
        )
