# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

import re

from sos.report.plugins import Plugin, PluginOpt, UbuntuPlugin, SoSPredicate


class OpenSearchDashboards(Plugin, UbuntuPlugin):
    short_desc = "Charmed OpenSearch Dashboards"
    plugin_name = "charmed_opensearchui"
    option_list = [
        PluginOpt(
            "user", default="admin", val_type=str,
            desc="Username for opensearch, to check APIs"
        ),
        PluginOpt(
            "password", default="", val_type=str,
            desc="Password for opensearch, to check APIs",
        )
    ]

    log_path = "/var/log/opensearch-dashboards"
    etc_path = "/etc/opensearch-dashboards"
    config_path = f"{etc_path}/opensearch_dashboards.yml"
    certificates_path = f"{etc_path}/certificates"
    node_config_path = f"{etc_path}/node.options"

    snap_current_path = "/var/snap/opensearch-dashboards/current"
    snap_common_path = "/var/snap/opensearch-dashboards/common"

    def setup(self):
        if not self.check_vm():
            return

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
        self.add_journal(units="snap.opensearch-dashboards.*", lines=1000,
                         allfields=True)

        # SERVICES
        self.add_service_status(
            "snap.opensearch-dashboards.exporter-daemon",
            suggest_filename="service_status_exporter_daemon"
        )
        self.add_service_status(
            "snap.opensearch-dashboards.opensearch-dashboards-daemon",
            suggest_filename="service_status_opensearch_dashboards_daemon"
        )
        self.add_copy_spec([
            "/etc/systemd/system/"
            "snap.opensearch-dashboards.exporter-daemon.service",
            "/etc/systemd/system/"
            "snap.opensearch-dashboards.opensearch-dashboards-daemon.service",
        ])

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
        host, port = self.get_hostname_port(
            opensearch_dashboard_config_file)
        base_url = f"http://{host}:{port}"
        self.export_api(base_url)

    def collect(self):
        # PORTS
        with self.collection_file('listening_ports') as pofile:
            ss_pred = SoSPredicate(self, kmods=['tcp_diag', 'udp_diag',
                                                'inet_diag'],
                                   required={'kmods': 'all'})
            res = self.exec_cmd("ss -tulpn", pred=ss_pred)
            if not res['status'] == 0:
                pofile.write(f"Unable to get ports list: {res['output']}")
                return
            lines = res['output'].splitlines()
            filtered_ports = [
                line for index, line in enumerate(lines)
                if index == 0 or "5601" in line
            ]
            pofile.writelines('\n'.join(filtered_ports) + '\n')

        # PROCESS TREE
        with self.collection_file('process_tree') as prfile:
            res = self.exec_cmd("ps aux")
            if not res['status'] == 0:
                prfile.write(f"Unable to get process list: {res['output']}")
                return
            lines = res['output'].splitlines()
            filtered_procs = [
                line for index, line in enumerate(lines)
                if index == 0 or "opensearch-dashboards" in line
            ]
            prfile.writelines('\n'.join(filtered_procs) + '\n')

    def check_vm(self):
        return self.path_exists(self.snap_current_path)

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

    def export_api(self, base_url):
        if not (password := self.get_option('password')):
            return
        base_cmd = f"curl -s -k -u {self.get_option('user')}:{password} -X GET"

        self.add_cmd_output(f"{base_cmd} '{base_url}/api/status'",
                            suggest_filename="status")

        self.add_cmd_output(f"{base_cmd} '{base_url}/api/stats?extended=true'",
                            suggest_filename="stats")

        query = ("type=dashboard&type=visualization&type=index-pattern&type"
                 "=search&per_page=1&fields=id")
        self.add_cmd_output(f"{base_cmd} "
                            f"'{base_url}/api/saved_objects/_find?{query}'",
                            suggest_filename="saved_object_count")

    def postproc(self):
        # SCRUB PASSWORDS
        if self.check_vm():
            opensearch_dashboard_config_file = (f"{self.snap_current_path}"
                                                f"{self.config_path}")
            self.do_path_regex_sub(
                f"{opensearch_dashboard_config_file}",
                r"(\s*opensearch\.password\s*:\s+).*",
                r'\1"*********"',
            )
