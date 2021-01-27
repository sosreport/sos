# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


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
