# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from sos_tests import StageTwoReportTest

KEYWORD = 'gibson'
LONG_DIR = '/tmp/sos-test-long-filename'
# fits within NAME_MAX, but exceeds it once each keyword is obfuscated
LONG_NAME = '-'.join([KEYWORD] * 30) + '.txt'


class LongObfuscatedFilenameTest(StageTwoReportTest):
    """Ensure that a filename that only exceeds NAME_MAX after obfuscation
    is still renamed, without retaining the original sensitive name.

    :avocado: tags=stagetwo
    """

    files = [('sos-test-long-filename.txt', f"{LONG_DIR}/{LONG_NAME}")]
    install_plugins = ['long_filename_test']
    sos_cmd = f"--clean -o long_filename_test --keywords {KEYWORD}"

    def pre_sos_setup(self):
        self.setup_isolated_cleaner_cache()

    def _get_collected_names(self):
        return os.listdir(self.get_name_in_archive(LONG_DIR))

    def test_original_name_not_retained(self):
        self.assertFileNotCollected(f"{LONG_DIR}/{LONG_NAME}")
        for name in self._get_collected_names():
            assert KEYWORD not in name, f"Found unobfuscated name {name}"

    def test_name_shortened_and_obfuscated(self):
        names = self._get_collected_names()
        assert len(names) == 1, f"Unexpected files collected: {names}"
        assert names[0].startswith('obfuscatedword'), \
            f"Name not obfuscated: {names[0]}"
        assert len(names[0].encode('utf-8')) <= 255, \
            f"Name exceeds NAME_MAX: {names[0]}"
        assert names[0].endswith('.txt'), \
            f"Extension not kept: {names[0]}"

    def test_content_obfuscated(self):
        name = self._get_collected_names()[0]
        self.assertFileNotHasContent(f"{LONG_DIR}/{name}", KEYWORD)

    def test_shortening_logged(self):
        self.assertSosLogContains('Obfuscated name exceeds 255 bytes')
