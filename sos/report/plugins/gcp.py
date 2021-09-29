# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import json
from http.client import HTTPResponse
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

    METADATA_ROOT = "http://metadata.google.internal/computeMetadata/v1/"
    METADATA_QUERY = "http://metadata.google.internal/computeMetadata/v1/" \
                     "?recursive=true"
    REDACTED = "[--REDACTED--]"

    # A line we will be looking for in the dmesg output. If it's there,
    # that means we're running on a Google Cloud Compute instance.
    GOOGLE_DMI = "DMI: Google Google Compute Engine/Google " \
                 "Compute Engine, BIOS Google"

    def check_enabled(self):
        """
        Checks if this plugin should be executed at all. In this case, it
        will check the `dmesg` command output to see if the system is
        running on a Google Cloud Compute instance.
        """
        dmesg = self.exec_cmd("dmesg")
        if dmesg['status'] != 0:
            return False
        return self.GOOGLE_DMI in dmesg['output']

    def setup(self):
        """
        Collect the following info:
         * Metadata from the Metadata server
         * `gcloud auth list` output
         * Any google services output from journal
        """

        # Capture gcloud auth list
        self.add_cmd_output("gcloud auth list", tags=['gcp'])

        # Get and store Metadata
        try:
            self.metadata = self.get_metadata()
            self.scrub_metadata()
            self.add_string_as_file(json.dumps(self.metadata, indent=4),
                                    "metadata.json", plug_dir=True,
                                    tags=['gcp'])
        except RuntimeError as err:
            self.add_string_as_file(str(err), 'metadata.json',
                                    plug_dir=True, tags=['gcp'])

        # Add journal entries
        self.add_journal(units="google*", tags=['gcp'])

    def get_metadata(self) -> dict:
        """
        Retrieves metadata from the Metadata Server and transforms it into a
        dictionary object.
        """
        response = self._query_address(self.METADATA_QUERY)
        response_body = response.read().decode()
        return json.loads(response_body)

    @staticmethod
    def _query_address(url: str) -> HTTPResponse:
        """
        Query the given url address with headers required by Google Metadata
        Server.
        """
        try:
            req = request.Request(url, headers={'Metadata-Flavor': 'Google'})
            response = request.urlopen(req)
        except URLError as err:
            raise RuntimeError(
                "Failed to communicate with Metadata Server: " + str(err))
        if response.code != 200:
            raise RuntimeError(
                f"Failed to communicate with Metadata Server "
                f"(code: {response.code}): " + response.read().decode())
        return response

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
            elif isinstance(data, list):
                return [scrub(value) for value in data]
            elif isinstance(data, str):
                return data.replace(project_number, self.REDACTED)\
                           .replace(project_id, self.REDACTED)
            elif isinstance(data, int):
                return self.REDACTED if data == project_number_int else data
            return data

        self.metadata = scrub(self.metadata)

        self.safe_redact_key(self.metadata['project']['attributes'],
                             'ssh-keys')
        self.safe_redact_key(self.metadata['project']['attributes'],
                             'sshKeys')

    @classmethod
    def safe_redact_key(cls, dict_obj: dict, key: str):
        if key in dict_obj:
            dict_obj[key] = cls.REDACTED
