# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest, StageTwoReportTest

import re


class ReportWithMask(StageOneReportTest):
    """Testing around basic --clean/--mask usage and expectations

    :avocado: tags=stageone
    """

    sos_cmd = '--mask -o host,networking'

    def test_mask_was_run(self):
        self.assertOutputContains('Beginning obfuscation')
        self.assertOutputContains('Obfuscation completed')

    def test_private_map_was_generated(self):
        self.assertOutputContains('A mapping of obfuscated elements is available at')
        map_file = re.findall('/.*sosreport-.*-private_map', self.cmd_output.stdout)[-1]
        self.assertFileExists(map_file)

    def test_tarball_named_obfuscated(self):
        self.assertTrue('obfuscated' in self.archive)

    def test_localhost_was_obfuscated(self):
        self.assertFileHasContent('/etc/hostname', 'host0')

    def test_ip_address_was_obfuscated(self):
        # Note: do not test for starting with the 100.* block here, as test
        # machines may have /32 addresses. Instead, test that the actual
        # IP address is not present
        self.assertFileNotHasContent('ip_addr', self.sysinfo['pre']['networking']['ip_addr'])

    def test_loopback_was_not_obfuscated(self):
        self.assertFileHasContent('ip_addr', '127.0.0.1/8')

    def test_mac_addrs_were_obfuscated(self):
        content = self.get_file_content('sos_commands/networking/ip_maddr_show')
        for line in content.splitlines():
            if line.strip().startswith('link'):
                mac = line.strip().split()[1]
                assert mac.startswith('53:4f:53'), "Found unobfuscated mac addr %s" % mac


class ReportWithCleanedKeywords(StageOneReportTest):
    """Testing for obfuscated keywords provided by the user

    :avocado: tags=stageone
    """

    sos_cmd = '--clean -o filesys,kernel --keywords=fstab,Linux'

    # Ok, sort of cheesy here but this does actually test filename changes on
    # a file common to all distros
    def test_filename_obfuscated(self):
        self.assertFileNotCollected('/etc/fstab')
        self.assertFileGlobInArchive('/etc/obfuscatedword*')

    def test_keyword_obfuscated_in_file(self):
        self.assertFileNotHasContent('sos_commands/kernel/uname_-a', 'Linux')


class DefaultRemoveBinaryFilesTest(StageTwoReportTest):
    """Testing that binary files are removed by default

    :avocado: tags=stagetwo
    """

    files = ['/var/log/binary_test.tar.xz']
    install_plugins = ['binary_test']
    sos_cmd = '--clean -o binary_test,kernel,host'

    def test_binary_removed(self):
        self.assertFileNotCollected('var/log/binary_test.tar.xz')

    def test_binaries_removed_reported(self):
        self.assertOutputContains('\[removed .* unprocessable files\]')


class KeepBinaryFilesTest(StageTwoReportTest):
    """Testing that --keep-binary-files will function as expected

    :avocado: tags=stagetwo
    """

    files = ['/var/log/binary_test.tar.xz']
    install_plugins = ['binary_test']
    sos_cmd = '--clean --keep-binary-files -o binary_test,kernel,host'

    def test_warning_message_shown(self):
        self.assertOutputContains(
            'WARNING: binary files that potentially contain sensitive information '
            'will NOT be removed from the final archive'
        )

    def test_binary_is_in_archive(self):
        self.assertFileCollected('var/log/binary_test.tar.xz')

    def test_no_binaries_reported_removed(self):
        self.assertOutputNotContains('\[removed .* unprocessable files\]')
