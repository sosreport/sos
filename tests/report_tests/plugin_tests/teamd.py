# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from avocado.utils import process
from sos_tests import StageTwoReportTest


class TeamdPluginTest(StageTwoReportTest):
    """Ensure that team device enumeration is working correctly, by creating
    a 'fake' team device. This inherently also tests proper iteration of
    add_device_cmd().

    :avocado: tags=stagetwo
    """

    packages = {
        'rhel': ['teamd', 'NetworkManager-team']
    }

    sos_cmd = '-o teamd'
    redhat_only = True

    def pre_sos_setup(self):
        # restart NetworkManager to account for the new package
        nmout = process.run('systemctl restart NetworkManager', timeout=30)
        assert nmout.exit_status == 0, "NetworkManager failed to restart"
        # create the team device
        res = process.run('nmcli con add type team ifname sostesting',
                          timeout=30)
        assert res.exit_status == 0, "Failed creating team device: %s" % res.stdout_text

    def post_test_tear_down(self):
        res = process.run('nmcli con delete team-sostesting', timeout=30)
        assert res.exit_status == 0, "Failed to delete temp team device: %s" % res.stdout_text

    def test_teamd_plugin_executed(self):
        self.assertPluginIncluded('teamd')

    def test_team_dev_iteration(self):
        self.assertFileGlobInArchive('sos_commands/teamd/*sostest*state')
        self.assertFileGlobInArchive('sos_commands/teamd/*sostesting_ports')
