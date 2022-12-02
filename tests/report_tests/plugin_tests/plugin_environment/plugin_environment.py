# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from sos_tests import StageTwoReportTest


class PluginDefaultEnvironmentTest(StageTwoReportTest):
    """
    Ensure that being able to set a default set of environment variables is
    working correctly and does not leave a lingering env var on the system

    :avocado: tags=stagetwo
    """

    install_plugins = ['default_env_test']
    sos_cmd = '-o default_env_test'

    def test_environment_used_in_cmd(self):
        self.assertFileHasContent(
            'sos_commands/default_env_test/env_var_test',
            'Does Linus play hockey?'
        )

    def test_environment_setting_logged(self):
        self.assertSosLogContains(
            'Default environment for all commands now set to'
        )

    def test_environment_not_set_on_host(self):
        self.assertTrue('TORVALDS' not in os.environ)
        self.assertTrue('GREATESTSPORT' not in os.environ)

    def test_environment_not_captured(self):
        # we should still have an empty environment file
        self.assertFileCollected('environment')
        self.assertFileNotHasContent('environment', 'TORVALDS')
        self.assertFileNotHasContent('environment', 'GREATESTSPORT')
