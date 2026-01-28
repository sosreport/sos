# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#
import os
import re
import tempfile

from sos.report.plugins import Plugin, PluginOpt, UbuntuPlugin, SoSPredicate


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

    netrc_path = ""
    hostname = "localhost"
    port = "9200"

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

    def check_enabled(self):
        return self.check_vm()

    def check_vm(self):
        return self.path_exists(self.snap_current_path)

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
                if index == 0 or f":{self.port}" in line
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
                if index == 0 or "opensearch" in line
            ]
            prfile.writelines('\n'.join(filtered_procs) + '\n')

    def get_hostname_port(self, opensearch_config_file):
        """ Get hostname and port number """
        try:
            with open(opensearch_config_file, encoding='UTF-8') as config:
                for line in config:
                    network_host = re.search(r'(^network.publish_host):(.*)',
                                             line)
                    network_port = re.search(r'(^http.port):(.*)', line)
                    if network_host and len(network_host.groups()) == 2:
                        self.hostname = re.sub(
                            r'"|\'',
                            '',
                            network_host.groups()[-1].strip()
                        )
                        continue
                    if network_port and len(network_port.groups()) == 2:
                        self.port = network_port.groups()[-1].strip()
        except Exception as err:  # pylint: disable=broad-except
            self._log_info(f"Failed to parse {opensearch_config_file}: {err}")

    def export_api(self, base_url):
        password = os.environ.get("OPENSEARCH_PWD",
                                  self.get_option('password'))
        if not password:
            self.soslog.warning(
                "dump_error: password are not provided, skipping API dumps."
            )
            return

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_netrc:
            temp_netrc.write(
                f"machine {self.hostname}"
                f" login {self.get_option('user')} password {password}\n")
            self.netrc_path = temp_netrc.name
            base_cmd = f"curl -k --netrc-file {self.netrc_path} -X GET"
            self.add_cmd_output(
                f"{base_cmd} '{base_url}/_cluster/settings?pretty'",
                suggest_filename="settings"
            )
            self.add_cmd_output(
                f"{base_cmd} '{base_url}/_cluster/health?pretty'",
                suggest_filename="health"
            )
            self.add_cmd_output(
                f"{base_cmd} '{base_url}/_cluster/stats?pretty'",
                suggest_filename="stats"
            )
            self.add_cmd_output(
                f"{base_cmd} '{base_url}/_cat/nodes?v'",
                suggest_filename="nodes"
            )
            self.add_cmd_output(
                f"{base_cmd} '{base_url}/_cat/indices'",
                suggest_filename="indices"
            )
            self.add_cmd_output(
                f"{base_cmd} '{base_url}/_cat/shards'",
                suggest_filename="shards"
            )
            self.add_cmd_output(
                f"{base_cmd} '{base_url}/_cat/aliases'",
                suggest_filename="aliases"
            )

    def postproc(self):
        if self.path_exists(self.netrc_path):
            os.remove(self.netrc_path)
        # SCRUB PASSWORDS
        if self.check_vm():
            opensearch_config_file = (f"{self.snap_current_path}"
                                      f"{self.config_path}")
            self.do_path_regex_sub(
                f"{opensearch_config_file}",
                r"(\s*plugins\.security\.ssl\..+password\s*:\s+).*",
                r'\1"*********"',
            )
