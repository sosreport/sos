# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from sos_tests import StageTwoReportTest


class ExistingDirectoryCleanSizeTest(StageTwoReportTest):
    """Ensure sos clean on a directory does not report Size from the
    directory inode. That value is filesystem metadata (often 4KiB),
    not the obfuscated data size.

    :avocado: tags=stagetwo
    """

    sos_cmd = ''
    sos_component = 'clean'

    def pre_sos_setup(self):
        src = os.path.join(self.tmpdir, 'src',
                           'sosreport-cleanertest-dirsize')
        os.makedirs(os.path.join(src, 'sos_logs'))
        with open(os.path.join(src, 'hostname'), 'w',
                  encoding='utf-8') as hfile:
            hfile.write('cleanertest.example.com\n')
        with open(os.path.join(src, 'sos_logs', 'sos.log'), 'w',
                  encoding='utf-8') as lfile:
            lfile.write('test log\n')
        map_file = os.path.join(self.tmpdir, 'default_mapping')
        self.sos_cmd = f'--no-update --map-file {map_file} {src}'

    def test_directory_output_omits_size(self):
        self.assertOutputContains(
            'The obfuscated archive is available at'
        )
        self.assertOutputNotContains('\tSize\t')
        self.assertOutputContains('\tOwner\t')
