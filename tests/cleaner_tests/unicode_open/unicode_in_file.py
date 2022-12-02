# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest


class UnicodeOpenTest(StageTwoReportTest):
    """This test ensures that we can safely open files that have embedded
    unicode in them, and that those files do not trigger an exception that
    leaves them uncleaned.

    :avocado: tags=stagetwo
    """

    sos_cmd = '--clean -o unicode_test,networking,host'
    files = [('sos-test-unicode.txt', '/tmp/sos-test-unicode.txt')]
    install_plugins = ['unicode_test']

    def test_file_was_collected(self):
        self.assertFileCollected('/tmp/sos-test-unicode.txt')

    def test_file_was_opened(self):
        # if this fails, then we hit an exception when opening the file
        self.assertSosLogContains('Obfuscating tmp/sos-test-unicode.txt')
        self.assertSosLogNotContains('.*Unable to parse.*')

    def test_obfuscation_complete(self):
        # make sure that we didn't stop processing the file after the unicode
        self.assertFileNotHasContent('tmp/sos-test-unicode.txt', '192.168.1.1')
