# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest


class DefaultCollectionsTest(StageTwoReportTest):
    """Ensure that the default collections are firing for Plugins based on
    their enablement triggers, which gives us more atomicity in Plugin design

    :avocado: tags=stagetwo
    """

    packages = {'rhel': 'cups',
                'Ubuntu': 'cups'}

    sos_cmd = '-o cups'

    def test_service_status_collected(self):
        self.assertFileCollected('sos_commands/cups/systemctl_status_cups')
        _m = self.get_plugin_manifest('cups')
        ent = None
        for cmd in _m['commands']:
            if cmd['exec'] == 'systemctl status cups':
                ent = cmd
        assert ent, "No manifest entry for systemctl status cups"

    def test_journal_collected(self):
        self.assertFileCollected('sos_commands/cups/journalctl_--no-pager_--unit_cups')
        _m = self.get_plugin_manifest('cups')
        ent = None
        for cmd in _m['commands']:
            if cmd['exec'] == 'journalctl --no-pager  --unit cups':
                ent = cmd
        assert ent, "No manifest entry for journalctl cups"

        assert 'journal_cups' in ent['tags'], "Journal tags not correct: %s" % ent['tags']
