# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest

ENTRA_BROKER_LOCATION = "/var/snap/authd-msentraid/current/broker.conf"

ENTRA_BROKER_CONF_EXPECTED = """[oidc]
issuer = https://login.microsoftonline.com/******/v2.0
client_id = ******
force_provider_authentication = false
"""

GOOGLE_BROKER_LOCATION = "/var/snap/authd-google/current/broker.conf"

GOOGLE_BROKER_CONF_EXPECTED = """[oidc]
issuer = https://accounts.google.com
client_id = ******
client_secret = ******
force_provider_authentication = false
"""


class AuthdTest(StageTwoReportTest):

    files = [
        ("entra_broker.conf", ENTRA_BROKER_LOCATION),
        ("google_broker.conf", GOOGLE_BROKER_LOCATION),
    ]

    ubuntu_only = True
    sos_cmd = "-o authd"

    def test_authd_scrubbed(self):
        self.assertPluginIncluded("authd")

        self.assertEqual(
            self.get_file_content(ENTRA_BROKER_LOCATION),
            ENTRA_BROKER_CONF_EXPECTED,
        )
        self.assertEqual(
            self.get_file_content(GOOGLE_BROKER_LOCATION),
            GOOGLE_BROKER_CONF_EXPECTED,
        )
