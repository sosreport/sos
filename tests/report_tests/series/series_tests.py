# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, and redistribute it subject to the terms and conditions
# of version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest


class SeriesTestBasic(StageTwoReportTest):
    """Basic series collection functionality

    :avocado: tags=stagetwo
    """
    install_plugins = ['series_test']
    sos_cmd = '-o series_test'

    def test_series_file_collected(self):
        self.assertFileCollected('sos_commands/series_test/date')
        self.assertFileCollected('sos_commands/series_test/date.1')
        self.assertFileCollected('sos_commands/series_test/date.2')

    def test_invalid_series_collected_once(self):
        self.assertFileCollected('sos_commands/series_test/uptime')
        self.assertFileNotCollected('sos_commands/series_test/uptime.1')

    def test_series_runs_logged(self):
        self.assertSosLogContains('run 1 of 3')
        self.assertSosLogContains('run 2 of 3')
        self.assertSosLogContains('run 3 of 3')

    def test_invalid_series_warns(self):
        self.assertSosLogContains('invalid series')

    def test_manifest_series_entries_and_spacing(self):
        cmds = self.get_plugin_manifest('series_test')['commands']
        date_runs = [cmd for cmd in cmds if cmd['exec'] == 'date']
        self.assertEqual(len(date_runs), 3)
        times = sorted(cmd['start_time'] for cmd in date_runs)
        for earlier, later in zip(times, times[1:]):
            self.assertGreaterEqual(later - earlier, 2)

    def test_manifest_single_entry_for_invalid_series(self):
        cmds = self.get_plugin_manifest('series_test')['commands']
        uptime_runs = [cmd for cmd in cmds if cmd['exec'] == 'uptime']
        self.assertEqual(len(uptime_runs), 1)
