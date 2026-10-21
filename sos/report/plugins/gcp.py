# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
from http.client import HTTPException
import json
from typing import Any
from urllib import request

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class GCP(Plugin, IndependentPlugin):

    short_desc = 'Google Cloud Platform'
    plugin_name = 'gcp'
    profiles = ('virt',)
    services = (
        'google-guest-agent',
        'google-guest-agent-manager',
        'google-guest-compat-manager',
        'google-osconfig-agent',
        'google-startup-scripts',
        'google-shutdown-scripts',
        'google-oslogin-cache',
        'google-cloud-ops-agent',
        'google-cloud-ops-agent-fluent-bit',
        'google-cloud-ops-agent-opentelemetry-collector',
        'gce-workload-cert-refresh',
    )

    option_list = [
        PluginOpt('keep-pii', default=False,
                  desc="Stop the plugin from removing PIIs like project name "
                       "or organization ID from the metadata retrieved from "
                       "Metadata server.")
    ]

    PRODUCT_PATH = "/sys/devices/virtual/dmi/id/product_name"

    METADATA_QUERY = (
        "http://metadata.google.internal/computeMetadata/v1/?recursive=true"
    )
    METADATA_IP_QUERY = (
        "http://169.254.169.254/computeMetadata/v1/?recursive=true"
    )
    REDACTED = "[--REDACTED--]"
    metadata = None

    def check_enabled(self):
        """
        Checks if this plugin should be executed based on the presence of
        GCE entry in sysfs.
        """
        try:
            with open(self.PRODUCT_PATH, encoding='utf-8') as sys_file:
                return "Google Compute Engine" in sys_file.read()
        except OSError:
            return False

    def setup(self):
        """
        Collect the following info:
         * `gcloud auth list` output
         * Guest Agent, MDS mTLS, OS Login, and Snapshot directory listings
         * Guest Agent, Ops Agent, and GPU installer configurations and logs
        """
        # Exclude private credentials, un-flushed Ops Agent disk buffers, and
        # downloaded GPU installer binaries/archives.
        self.add_forbidden_path([
            "/run/google-mds-mtls/*.key",
            "/etc/google/auth/*",
            "/var/lib/google-cloud-ops-agent/fluent-bit/buffers/*",
            "/opt/google/cuda-installer/*.run",
            "/opt/google/cuda-installer/*.deb",
            "/opt/google/cuda-installer/*.rpm",
            "/opt/google/cuda-installer/*.tar*",
            "/opt/google/cuda-installer/*.pyz",
        ])

        self.add_copy_spec([
            # Google Guest Agent & Plugin Manager (2025+ modular architecture)
            "/etc/default/instance_configs.cfg",
            "/etc/default/instance_configs.cfg.distro",
            "/etc/default/instance_configs.cfg.template",
            "/etc/google-guest-agent/",
            "/var/lib/google-guest-agent/*/agent_state/plugin_info/*",
            "/var/lib/google-guest-agent/*/agent_state/plugins/*/*.log*",
            "/var/log/google-guest-agent*.log*",
            # Google Cloud Ops Agent
            "/etc/google-cloud-ops-agent/config.yaml",
            "/etc/systemd/system/google-cloud-ops-agent*.d/*",
            "/var/log/google-cloud-ops-agent/*.log*",
            "/var/log/google-cloud-ops-agent/subagents/*.log*",
            # Google Cloud GPU / CUDA Installer & Kernel Header Postinst Hook
            "/opt/google/cuda-installer/",
            "/var/log/cuda-installer.log*",
            "/var/log/google-gpu-installer.log*",
            "/var/log/cos-gpu-installer.log*",
            "/etc/kernel/postinst.d/zz-gcp-gpu-header-check",
        ])

        self.add_cmd_output([
            "gcloud auth list",
            "ip -d route show table local",
            "ip -6 -d route show table local",
        ], tags=['gcp'])

        self.add_dir_listing([
            "/run/google-guest-agent",
            "/var/lib/google-guest-agent",
        ], recursive=True, tags=['gcp'])

        self.add_dir_listing([
            "/run/google-mds-mtls",
            "/run/systemd/notify",
            "/usr/lib/google/guest_agent",
            "/usr/lib64/google/guest_agent",
            "/etc/sudoers.d",
            "/var/google-sudoers.d",
            "/etc/google/snapshots",
            "/etc/google/auth",
        ], tags=['gcp'])

    def collect(self):
        # Collect Metadata from the server before opening the collection file
        # so failed MDS queries do not leave an empty 0-byte metadata.json.
        try:
            self.metadata = self.get_metadata()
            self.scrub_metadata()
            with self.collection_file('metadata.json', tags=['gcp']) as mfile:
                mfile.write(json.dumps(self.metadata, indent=4))
        except (RuntimeError, ValueError, OSError) as err:
            self._log_info(f"Could not collect GCE metadata: {err}")

        # Collect zone.txt file from RHUI
        curl_command = ('curl -v --connect-timeout 10 '
                        'https://rhui.googlecloud.com/zone.txt')

        rhui_package = self.policy.package_manager.all_pkgs_by_name_regex(
            r'google-rhui-client')
        if rhui_package:
            self.collect_cmd_output(curl_command)

    def get_metadata(self) -> dict:
        """
        Retrieves metadata from the Metadata Server and transforms it into a
        dictionary object. Falls back to the link-local IP (169.254.169.254)
        when guest DNS resolution for metadata.google.internal fails.
        """
        last_err = None
        for url in (self.METADATA_QUERY, self.METADATA_IP_QUERY):
            try:
                response_body = self._query_address(url)
                return json.loads(response_body)
            except (RuntimeError, ValueError, OSError) as err:
                last_err = err
        raise last_err

    def _query_address(self, url: str) -> str:
        """
        Query the given url address with headers required by Google Metadata
        Server, bypassing system HTTP proxy environment variables.
        """
        try:
            req = request.Request(url, headers={'Metadata-Flavor': 'Google'})
            opener = request.build_opener(request.ProxyHandler({}))
            with opener.open(req, timeout=5) as response:
                if response.code != 200:
                    raise RuntimeError(
                        f"Failed to communicate with Metadata Server "
                        f"(code: {response.code}): " +
                        response.read().decode())
                return response.read().decode()
        except (OSError, HTTPException) as err:
            raise RuntimeError(
                "Failed to communicate with Metadata Server: " + str(err)) \
                from err

    def scrub_metadata(self):
        """
        Remove all PII information from metadata, unless a keep-pii option
        is specified.

        Note: PII information collected by this plugin, like
        project number, account names etc. might be required by Google
        Cloud Support for faster issue resolution.
        """
        if self.get_option('keep-pii'):
            return

        project = self.metadata.get('project', {})
        project_id = project.get('projectId')
        project_number_int = project.get('numericProjectId')
        project_number = (
            str(project_number_int)
            if project_number_int is not None
            else None
        )

        def scrub(data: Any) -> Any:
            if isinstance(data, dict):
                if 'token' in data:
                    # Data returned for recursive query shouldn't contain
                    # tokens, but you can't be too careful.
                    data['token'] = self.REDACTED
                return {scrub(k): scrub(v) for k, v in data.items()}
            if isinstance(data, list):
                return [scrub(value) for value in data]
            if isinstance(data, str):
                if project_number:
                    data = data.replace(project_number, self.REDACTED)
                if project_id:
                    data = data.replace(project_id, self.REDACTED)
                return data
            if isinstance(data, int):
                return (
                    self.REDACTED
                    if project_number_int is not None
                    and data == project_number_int
                    else data
                )
            return data

        self.metadata = scrub(self.metadata)

        # Redact sensitive attribute values in-place after metadata collection
        # while preserving the attribute keys in metadata.json.
        sensitive_attr_keys = (
            'kube-env',
            'ssh-keys',
            'sshKeys',
            'windows-keys',
            'startup-script',
            'shutdown-script',
            'user-data',
        )
        sensitive_attr_prefixes = (
            'startup-script-',
            'shutdown-script-',
            'windows-startup-script-',
            'windows-shutdown-script-',
            'sysprep-specialize-script-',
        )
        for section in ('project', 'instance'):
            attrs = self.metadata.get(section, {}).get('attributes')
            if isinstance(attrs, dict):
                for key in sensitive_attr_keys:
                    self.safe_redact_key(attrs, key)
                for key in list(attrs.keys()):
                    if isinstance(key, str) and key.startswith(
                        sensitive_attr_prefixes
                    ):
                        self.safe_redact_key(attrs, key)

    def postproc(self):
        # e.g. password: my_secret_password -> password: ******
        #      credentials: bearer_token_xyz -> credentials: ******
        self.do_file_sub(
            "/etc/google-cloud-ops-agent/config.yaml",
            r'([a-zA-Z0-9_.-]*'
            r'(?:password|secret|token|api_key|access_key|private_key'
            r'|credentials)'
            r'[a-zA-Z0-9_.-]*[ \t]*:[ \t]*)[^\s#]+',
            r'\1******',
        )
        self.do_paths_http_sub([
            "/etc/google-cloud-ops-agent/config.yaml",
        ])

    @classmethod
    def safe_redact_key(cls, dict_obj: dict, key: str):
        """ Redact keys """
        if key in dict_obj:
            dict_obj[key] = cls.REDACTED
