# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageOneReportTest


class CommandPriorityTest(StageOneReportTest):
    """Ensure that the priority parameter for command execution is functioning
    as expected

    :avocado: tags=stageone
    """

    sos_cmd = '-o logs,process'

    def test_logs_full_journal_correct_priority(self):
        cmds = self.get_plugin_manifest('logs')['commands']
        fullj = cmds[-1]
        self.assertEqual(fullj['priority'], 100)

    def test_logs_full_journal_run_last(self):
        cmds = self.get_plugin_manifest('logs')['commands']
        cmds.sort(key=lambda x: x['start_time'])
        # journal_full should be the last command executed
        self.assertTrue('journal_full' in cmds[-1]['tags'])

    def test_process_correct_priorities(self):
        cmds = self.get_plugin_manifest('process')['commands']
        # ensure root symlinked ps ran first
        self.assertTrue(cmds[0]['priority'] == 1 and 'ps_aux' in cmds[0]['tags'])

        # get lsof and iotop command entries
        _lsof = None
        _iotop = None
        for cmd in cmds:
            if cmd['command'] == 'lsof':
                _lsof = cmd
            elif cmd['command'] == 'iotop':
                _iotop = cmd

        self.assertTrue(_lsof and _iotop, "lsof or iotop output missing")

        self.assertEqual(_lsof['priority'], 50)
        self.assertEqual(_iotop['priority'], 100)
        self.assertTrue(_lsof['start_time'] < _iotop['start_time'])

            
        
