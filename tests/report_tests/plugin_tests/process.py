# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import glob
import os

from sos_tests import StageOneReportTest


class ProcessPluginTest(StageOneReportTest):
    """
    :avocado: tags=stageone
    """

    sos_cmd = '-o process -k process.numprocs=100'

    def test_proc_files_collected(self):
        self.assertFileGlobInArchive('/proc/*/status')
        self.assertFileGlobInArchive('/proc/*/stack')
        self.assertFileGlobInArchive('/proc/*/oom_*')

    def test_option_limited_proc_collection(self):
        count = glob.glob(os.path.join(self.archive_path, 'proc/*/status'))
        self.assertTrue(len(count) < 101)
