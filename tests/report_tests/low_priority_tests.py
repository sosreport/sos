# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from os.path import exists
from sos_tests import StageOneReportTest


class LowPrioTest(StageOneReportTest):
    """
    Ensures that --low-priority properly sets our defined constraints on our
    own process

    :avocado: tags=stageone
    """

    sos_cmd = '--low-priority -o kernel'

    def test_ionice_class_set(self):
        _class = self.manifest['components']['report']['priority']['io_class']
        if exists('/usr/bin/ionice'):
            self.assertSosLogContains('Set IO class to idle')
            self.assertEqual(_class, 'idle')
        else:
            self.assertEqual(_class, 'unknown')

    def test_niceness_set(self):
        self.assertSosLogContains('Set niceness of report to 19')
        self.assertEqual(self.manifest['components']['report']['priority']['niceness'], 19)
