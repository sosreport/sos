# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import json
from typing import Any
from urllib import request
from urllib.error import URLError

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class GCP(Plugin, IndependentPlugin):

    short_desc = 'Google Cloud Platform'
    plugin_name = 'gcp'
    profiles = ('virt',)

    option_list = [
        PluginOpt('keep-pii', default=False,
                  desc="Stop the plugin from removing PIIs like project name "
                       "or organization ID from the metadata retrieved from "
                       "Metadata server.")
    ]

    PRODUCT_PATH = "/sys/devices/virtual/dmi/id/product_name"

    METADATA_QUERY = "http://metadata.google.internal/computeMetadata/v1/" \
                     "?recursive=true"
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
         * Any google services output from journal
        """

        # Capture gcloud auth list
        self.add_cmd_output("gcloud auth list", tags=['gcp'])

        # Add journal entries
        self.add_journal(units="google*", tags=['gcp'])

    def collect(self):
        # Collect Metadata from the server
        with self.collection_file('metadata.json', tags=['gcp']) as mfile:
            try:
                self.metadata = self.get_metadata()
                self.scrub_metadata()
                mfile.write(json.dumps(self.metadata, indent=4))
            except RuntimeError as err:
                mfile.write(str(err))

        # Collect zone.txt file from RHUI
        curl_command = ('curl -v --connect-timeout 10'
                        'https://rhui.googlecloud.com/zone.txt')

        rhui_package = self.policy.package_manager.all_pkgs_by_name_regex(
            r'google-rhui-client')
        if rhui_package:
            self.collect_cmd_output(curl_command)

    def get_metadata(self) -> dict:
        """
        Retrieves metadata from the Metadata Server and transforms it into a
        dictionary object.
        """
        response_body = self._query_address(self.METADATA_QUERY)
        return json.loads(response_body)

    def _query_address(self, url: str) -> str:
        """
        Query the given url address with headers required by Google Metadata
        Server.
        """
        try:
            req = request.Request(url, headers={'Metadata-Flavor': 'Google'})
            with request.urlopen(req) as response:
                if response.code != 200:
                    raise RuntimeError(
                        f"Failed to communicate with Metadata Server "
                        f"(code: {response.code}): " +
                        response.read().decode())
                return response.read().decode()
        except URLError as err:
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

        project_id = self.metadata['project']['projectId']
        project_number_int = self.metadata['project']['numericProjectId']
        project_number = str(project_number_int)

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
                return data.replace(project_number, self.REDACTED)\
                           .replace(project_id, self.REDACTED)
            if isinstance(data, int):
                return self.REDACTED if data == project_number_int else data
            return data

        self.metadata = scrub(self.metadata)

        self.safe_redact_key(self.metadata['project']['attributes'],
                             'ssh-keys')
        self.safe_redact_key(self.metadata['project']['attributes'],
                             'sshKeys')

    @classmethod
    def safe_redact_key(cls, dict_obj: dict, key: str):
        """ Redact keys """
        if key in dict_obj:
            dict_obj[key] = cls.REDACTED
