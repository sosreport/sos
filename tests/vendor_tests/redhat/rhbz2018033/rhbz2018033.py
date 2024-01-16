# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest


class rhbz2018033(StageTwoReportTest):
    """Test that control of plugin timeouts is independent of other plugin
    timeouts. See #2744.

    https://bugzilla.redhat.com/show_bug.cgi?id=2018033

    :avocado: tags=stagetwo
    """

    install_plugins = ['timeout_test']
    sos_cmd = ('-vvv -o timeout_test,networking '
               '-k timeout_test.timeout=1 --plugin-timeout=123')

    def test_timeouts_separate(self):
        self.assertSosUILogContains('Plugin timeout_test timed out')
        self.assertSosUILogNotContains('Plugin networking timed out')

    def test_timeout_manifest_recorded(self):
        testm = self.get_plugin_manifest('timeout_test')
        self.assertTrue(testm['timeout_hit'])
        self.assertTrue(testm['timeout'] == 1)

        netm = self.get_plugin_manifest('networking')
        self.assertFalse(netm['timeout_hit'])
        self.assertTrue(netm['timeout'] == 123)
