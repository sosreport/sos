# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest

MOCK_FILE = '/tmp/sos-test-ipv6.txt'


class IPv6Test(StageTwoReportTest):
    """Place artificial plugin collecting crafted text file with ipv6 adresses
    to make sure ipv6 obfuscation works when calling 'sos clean' like a user
    would.

    :avocado: tags=stagetwo
    """

    install_plugins = ['ipv6']
    sos_cmd = '--clean -o ipv6'
    sos_timeout = 600
    # replace default mapping to avoid being influenced by previous runs
    # place mock file with crafted address used by mocked plugin
    files = [
        ('default_mapping', '/etc/sos/cleaner/default_mapping'),
        ('sos-test-ipv6.txt', MOCK_FILE)
    ]

    def test_valid_ipv6(self):
        self.assertFileCollected(MOCK_FILE)
        self.assertFileHasContent(MOCK_FILE, 'GOOD_IP=')
        self.assertFileNotHasContent(
            MOCK_FILE,
            'GOOD_IP=3000:505f:505f:505f:505f:505f:505f:505f'
        )

    def test_bad_ipv6(self):
        self.assertFileHasContent(MOCK_FILE, 'BAD_IP=')
        self.assertFileNotHasContent(
            MOCK_FILE,
            'BAD_IP=505f:505f:505f:505f:505f:505f:505f:505f'
        )
