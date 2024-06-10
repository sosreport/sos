# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest, StageTwoReportTest

import re
from os import stat


class ReportWithMask(StageOneReportTest):
    """Testing around basic --clean/--mask usage and expectations

    :avocado: tags=stageone
    """

    sos_cmd = '--mask -o host,networking'
    hosts_obfuscated = None

    def pre_sos_setup(self):
        # obfuscate a random word from /etc/hosts and ensure the updated
        # sanitised file has same permissions (a+r)
        try:
            self.hosts_obfuscated = open(
                '/etc/hosts').read().strip('#\n').split()[-1]
        except (FileNotFoundError, IndexError) as e:
            self.warning(f"Unable to process /etc/hosts: {e}")
        if self.hosts_obfuscated:
            self.sos_cmd += f' --keywords={self.hosts_obfuscated}'

    def test_mask_was_run(self):
        self.assertOutputContains('Beginning obfuscation')
        self.assertOutputContains('Obfuscation completed')

    def test_private_map_was_generated(self):
        self.assertOutputContains(
            'A mapping of obfuscated elements is available at')
        map_file = re.findall(
            '/.*sosreport-.*-private_map', self.cmd_output.stdout)[-1]
        self.assertFileExists(map_file)

    def test_tarball_named_obfuscated(self):
        self.assertTrue('obfuscated' in self.archive)

    def test_archive_type_correct(self):
        self.assertSosLogContains('Loaded .* as type sos report directory')

    def test_localhost_was_obfuscated(self):
        self.assertFileHasContent('hostname', 'host0')

    def test_ip_address_was_obfuscated(self):
        # Note: do not test for starting with the 100.* block here, as test
        # machines may have /32 addresses. Instead, test that the actual
        # IP address is not present
        self.assertFileNotHasContent(
            'ip_addr',
            self.sysinfo['pre']['networking']['ip_addr']
        )

    def test_loopback_was_not_obfuscated(self):
        self.assertFileHasContent('ip_addr', '127.0.0.1/8')

    def test_mac_addrs_were_obfuscated(self):
        content = self.get_file_content(
            'sos_commands/networking/ip_maddr_show'
        )
        for line in content.splitlines():
            if line.strip().startswith('link'):
                mac = line.strip().split()[1]
                assert \
                    mac.startswith('53:4f:53'), \
                    f"Found unobfuscated mac addr {mac}"

    def test_perms_unchanged_on_modified_file(self):
        if self.hosts_obfuscated:
            imode_orig = stat('/etc/hosts').st_mode
            imode_obfuscated = stat(
                self.get_name_in_archive('etc/hosts')).st_mode
            self.assertEqual(imode_orig, imode_obfuscated)


class ReportWithUserCustomisations(StageOneReportTest):
    """Testing for 1) obfuscated keywords provided by the user (--keywords
    option), and 2) skipping to clean specific files (--skip-cleaning-files
    option)

    :avocado: tags=stageone
    """

    sos_cmd = ('--clean -o filesys,kernel --keywords=fstab,Linux,tmp,'
               'BOOT_IMAGE,fs.dentry-state --skip-cleaning-files '
               'proc/cmdline,sos_commands/*/sysctl* --no-update')

    # Will the 'tmp' be properly treated in path to working dir without
    # raising an error?
    # To make this test effective, we assume the test runs on a system / with
    # Policy returning '/var/tmp' as temp.dir
    def test_keyword_in_tempdir_path(self):
        self.assertOutputContains(
            'Your sos report has been generated and saved in:'
        )
        self.assertTrue('tmp/' in self.archive)

    # Ok, sort of cheesy here but this does actually test filename changes on
    # a file common to all distros
    def test_filename_obfuscated(self):
        self.assertFileNotCollected('/etc/fstab')
        self.assertFileGlobInArchive('/etc/obfuscatedword*')

    def test_keyword_obfuscated_in_file(self):
        self.assertFileNotHasContent('sos_commands/kernel/uname_-a', 'Linux')

    def test_skip_cleaning_single_file(self):
        self.assertFileHasContent('proc/cmdline', 'BOOT_IMAGE')

    def test_skip_cleaning_glob_file(self):
        self.assertFileHasContent(
            'sos_commands/kernel/sysctl_-a',
            'fs.dentry-state'
        )


class DefaultRemoveBinaryFilesTest(StageTwoReportTest):
    """Testing that binary files are removed by default

    :avocado: tags=stagetwo
    """

    files = [('binary_test.tar.xz', '/var/log/binary_test.tar.xz')]
    install_plugins = ['binary_test']
    sos_cmd = '--clean -o binary_test,kernel,host'

    def test_binary_removed(self):
        self.assertFileNotCollected('var/log/binary_test.tar.xz')

    def test_binaries_removed_reported(self):
        self.assertOutputContains(r'\[removed .* unprocessable files\]')


class KeepBinaryFilesTest(StageTwoReportTest):
    """Testing that --keep-binary-files will function as expected

    :avocado: tags=stagetwo
    """

    files = [('binary_test.tar.xz', '/var/log/binary_test.tar.xz')]
    install_plugins = ['binary_test']
    sos_cmd = '--clean --keep-binary-files -o binary_test,kernel,host'

    def test_warning_message_shown(self):
        self.assertOutputContains(
            'WARNING: binary files that potentially contain sensitive '
            'information will NOT be removed from the final archive'
        )

    def test_binary_is_in_archive(self):
        self.assertFileCollected('var/log/binary_test.tar.xz')

    def test_no_binaries_reported_removed(self):
        self.assertOutputNotContains(r'\[removed .* unprocessable files\]')
