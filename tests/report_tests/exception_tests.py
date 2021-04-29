# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportExceptionTest, StageOneReportTest


class InvalidPluginEnabledTest(StageOneReportExceptionTest):
    """
    :avocado: tags=stageone
    """

    sos_cmd = '-o foobar'

    def test_caught_invalid_plugin(self):
        self.assertOutputContains('a non-existing plugin \(foobar\)')


class InvalidPluginOptionTest(StageOneReportExceptionTest):
    """
    :avocado: tags=stageone
    """

    sos_cmd = '-o kernel -k kernel.colonel=on'

    def test_caught_invalid_plugin_option(self):
        self.assertOutputContains('no such option "colonel" for plugin \(kernel\)')


class InvalidReportOptionTest(StageOneReportExceptionTest):
    """
    :avocado: tags=stageone
    """

    sos_cmd = '--magic'

    def test_caught_invalid_option(self):
        self.assertOutputContains('unrecognized arguments\: --magic')


class InvalidPluginDisableTest(StageOneReportTest):
    """Ensure passing an invalid plugin name for skipping does not stop the
    execution, see PR#2517

    :avocado: tags=stageone
    """
    sos_cmd = '-n logs,foobar,networking'

    def test_caught_invalid_plugin_name(self):
        self.assertOutputContains("Requested to skip non-existing plugin 'foobar'")
