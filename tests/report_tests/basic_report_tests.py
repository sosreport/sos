# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageOneReportTest


class NormalSoSReport(StageOneReportTest):
    """
    :avocado: tags=stageone
    """

    sos_cmd = '-v --label thisismylabel'

    def test_debug_in_logs_verbose(self):
        self.assertSosLogContains('DEBUG')

    def test_debug_not_printed_to_console(self):
        self.assertOutputNotContains('added cmd output')
        self.assertOutputNotContains('\[archive:.*\]')

    def test_postproc_called(self):
        self.assertSosLogContains('substituting scrpath')

    def test_label_applied_to_archive(self):
        self.assertTrue('thisismylabel' in self.archive)

    def test_free_symlink_created(self):
        self.assertFileCollected('free')


class LogLevelTest(StageOneReportTest):
    """
    :avocado: tags=stageone
    """

    sos_cmd = '-vvv -o kernel,host,boot,filesys'

    def test_archive_logging_enabled(self):
        self.assertSosLogContains('DEBUG: \[archive:.*\]')
        self.assertSosLogContains('Making leading paths for')

    def test_debug_printed_to_console(self):
        self.assertOutputContains('\[plugin:.*\]')


class RestrictedSoSReport(StageOneReportTest):
    """
    :avocado: tags=stageone
    """

    sos_cmd = '-o kernel,host,sudo,hardware,dbus,x11 --no-env-var --no-report -t1 --no-postproc'

    def test_no_env_vars_collected(self):
        self.assertFileNotCollected('environment')

    def test_no_reports_generated(self):
        self.assertFileNotCollected('sos_reports/sos.html')
        self.assertFileNotCollected('sos_reports/sos.json')
        self.assertFileNotCollected('sos_reports/sos.txt')

    def test_was_single_threaded_run(self):
        self.assertOutputNotContains('Finishing plugins')

    def test_postproc_not_called(self):
        self.assertOutputNotContains('substituting')

    def test_only_selected_plugins_run(self):
        self.assertOnlyPluginsIncluded(['kernel', 'host', 'sudo', 'hardware', 'dbus', 'x11'])


class DisabledCollectionsReport(StageOneReportTest):
    """
    :avocado: tags=stageone
    """

    sos_cmd = "-n networking,system,logs --skip-files=/etc/fstab --skip-commands='journalctl*'"

    def test_plugins_disabled(self):
        self.assertPluginNotIncluded('networking')
        self.assertPluginNotIncluded('system')
        self.assertPluginNotIncluded('logs')

    def test_skipped_plugins_have_no_dir(self):
        self.assertFileNotCollected('sos_commands/networking/')
        self.assertFileNotCollected('sos_commands/system/')
        self.assertFileNotCollected('sos_commands/logs/')

    def test_skip_files_working(self):
        self.assertFileNotCollected('/etc/fstab')

    def test_skip_commands_working(self):
        self.assertFileGlobNotInArchive('sos_commands/*/journalctl*')

