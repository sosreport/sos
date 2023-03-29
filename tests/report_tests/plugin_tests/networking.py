# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from sos_tests import StageOneReportTest


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
                    "sos_commands/networking/ethtool_*_%s" % dev
                )
