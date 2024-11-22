# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest

DO_SKIP = '/tmp/sos-test-version.txt'
NO_SKIP = '/tmp/sos-test-version-noskip'


class SkipVersionIPParser(StageTwoReportTest):
    """Ensures that we _skip_ files ending in 'version' (or 'version.txt') to
    avoid incorrectly obfuscating version numbers.

    :avocado: tags=stagetwo
    """

    files = [
        ('sos-test-version.txt', DO_SKIP),
        ('sos-test-version-noskip', NO_SKIP)
    ]
    install_plugins = ['skip_versions']
    sos_cmd = '--clean -o skip_versions'

    def test_version_file_skipped(self):
        self.assertFileCollected(DO_SKIP)
        self.assertFileHasContent(DO_SKIP, '10.11.12.13')
        self.assertFileHasContent(DO_SKIP, '6.0.0.1')

    def test_incorrect_version_file_not_skipped(self):
        self.assertFileCollected(NO_SKIP)
        self.assertFileNotHasContent(NO_SKIP, '10.11.12.13')
        self.assertFileNotHasContent(NO_SKIP, '6.0.0.1')
