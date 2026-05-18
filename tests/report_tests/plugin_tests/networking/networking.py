# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from sos_tests import StageOneReportTest, StageTwoReportTest


class NetworkingPluginTest(StageOneReportTest):
    """
    Basic tests to ensure proper collection from the networking plugins

    :avocado: tags=stageone
    """

    sos_cmd = '-o networking'

    def test_common_files_collected(self):
        self.assertFileCollected('/etc/resolv.conf')
        self.assertFileCollected('/etc/hosts')

    def test_ip_addr_symlink_created(self):
        self.assertFileCollected('ip_addr')

    def test_forbidden_globs_skipped(self):
        self.assertFileGlobNotInArchive('/proc/net/rpc/*/channel')
        self.assertFileGlobNotInArchive('/proc/net/rpc/*/flush')

    def test_netdevs_properly_iterated(self):
        for dev in os.listdir('/sys/class/net'):
            # some file(s) in the dir might not be real netdevs, see e.g.
            # https://lwn.net/Articles/142330/
            if not dev.startswith('bonding_'):
                self.assertFileGlobInArchive(
                    f"sos_commands/networking/ethtool_*_{dev}"
                )


class NetplanScrubTest(StageTwoReportTest):
    """
    ensure that netplan configuration is collected and that secret-bearing
    or uniquely-identifying YAML keys are scrubbed correctly

    :avocado: tags=stagetwo
    """

    sos_cmd = '-o networking'

    files = [
        ('90-NM-d377ae8e-fff5-11ee-bd96-07ef2a5f9e02.yaml',
         '/etc/netplan/90-NM-d377ae8e-fff5-11ee-bd96-07ef2a5f9e02.yaml'),
        ('99-sos-secrets.yaml',
         '/etc/netplan/99-sos-secrets.yaml'),
    ]
    ubuntu_only = True

    def test_netplan_wifi_password_scrubbed(self):
        self.assertFileNotHasContent(
            '/etc/netplan/90-NM-d377ae8e-fff5-11ee-bd96-07ef2a5f9e02.yaml',
            'awifipasswordforauth')

    def test_netplan_8021x_auth_scrubbed(self):
        for secret in ('an8021xpassword', 'an8021xidentity',
                       'an8021xanonid', 'aclientkeypass'):
            self.assertFileNotHasContent(
                '/etc/netplan/99-sos-secrets.yaml', secret)

    def test_netplan_wireguard_keys_scrubbed(self):
        for secret in ('aWGPrivateKey', 'aPeerPublicKey', 'aPresharedKey'):
            self.assertFileNotHasContent(
                '/etc/netplan/99-sos-secrets.yaml', secret)

    def test_netplan_gre_key_scrubbed(self):
        # GRE integer key on the `key:` field must be redacted too
        self.assertFileNotHasContent(
            '/etc/netplan/99-sos-secrets.yaml', 'key: 31337')

    def test_netplan_keymgmt_preserved(self):
        # `key-management` is a method name, not a secret - must stay visible
        self.assertFileHasContent(
            '/etc/netplan/99-sos-secrets.yaml', 'key-management')
