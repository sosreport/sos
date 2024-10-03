# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest, StageTwoReportTest


class SudoPluginTest(StageOneReportTest):
    """Basic sanity check to make sure common config files are collected

    :avocado: tags=stageone
    """

    sos_cmd = '-o sudo'

    def test_sudo_conf_collected(self):
        self.assertFileCollected('/etc/sudo.conf')
        self.assertFileCollected('/etc/sudoers')


class SudoLdapScrubbedTest(StageTwoReportTest):
    """Ensure that sudo conf is picked up and properly scrubbed

    :avocado: tags=stagetwo,scrub
    """

    sos_cmd = '-o sudo'
    files = [('sudo-ldap.conf', '/etc/sudo-ldap.conf')]

    def test_bindpw_scrubbed(self):
        self.assertFileNotHasContent('/etc/sudo-ldap.conf', 'sostestpassword')
