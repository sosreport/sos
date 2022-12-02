# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest


class SosExtrasPluginTest(StageTwoReportTest):
    """Ensure that the sos_extras plugin is properly executing command and
    file collections as defined in the sos_extras config file

    :avocado: tags=stagetwo
    """

    files = [('sos_testing.conf', '/etc/sos/extras.d/sos_testing.conf')]
    # rather than only enabling this plugin, make sure the enablement trigger
    # is working
    sos_cmd = '-n logs,networking,devicemapper,filesys,systemd'

    def test_extras_enabled(self):
        self.assertPluginIncluded('sos_extras')

    def test_setup_message_displayed(self):
        self.assertOutputContains('Collecting data from extras file /etc/sos/extras.d/sos_testing.conf')

    def test_extras_config_parsed(self):
        self.assertFileCollected('/etc/fstab')
        self.assertFileCollected('sos_commands/sos_extras/sos_testing.conf/echo_sos_test')
