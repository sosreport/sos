# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageTwoReportTest


class rhbz1950350(StageTwoReportTest):
    """Ensure that when `--clean` is used with report that the config settings
    from sos.conf under the [clean] section are loaded as well

    :avocado: tags=stagetwo
    """

    files = [
        ('sos.conf', '/etc/sos/sos.conf'),
        ('sos_clean_config.conf', '/etc/sos/extras.d/sos_clean_config.conf'),
        ('clean_config_test.txt', '/var/log/clean_config_test.txt')
    ]

    sos_cmd = '-v -o sos_extras --clean'

    def test_clean_config_loaded(self):
        self.assertSosLogContains("effective options now: (.*)? --clean --domains (.*)? --keywords (.*)?")

    def test_clean_config_performed(self):
        self.assertFileCollected('var/log/clean_config_test.txt')
        self.assertFileHasContent('var/log/clean_config_test.txt', 'The domain example.com should not be removed.')
        self.assertFileNotHasContent(
            'var/log/clean_config_test.txt',
            "This line contains 'shibboleth' which should be scrubbed."
        )
        self.assertFileNotHasContent('var/log/clean_config_test.txt', 'sosexample.com')
