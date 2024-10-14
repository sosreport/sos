# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest, StageTwoReportTest, redhat_only


class SystemPluginTest(StageOneReportTest):
    """Basic sanity check to make sure common config files are collected

    :avocado: tags=stageone
    """

    sos_cmd = '-o system'

    def test_system_files_collected(self):
        self.assertFileGlobInArchive("/proc/sys")
        self.assertFileGlobInArchive("/etc/default")
        self.assertFileGlobInArchive("/etc/environment")

    @redhat_only
    def test_system_files_collected_RH(self):
        self.assertFileGlobInArchive("/etc/sysconfig")

    def test_system_files_forbidden(self):
        self.assertFileGlobNotInArchive("/proc/sys/net/ipv4/route/flush")
        self.assertFileGlobNotInArchive("/proc/sys/net/ipv6/route/flush")
        self.assertFileGlobNotInArchive("/proc/sys/net/ipv6/neigh/" +
                                        "*/retrans_time")
        self.assertFileGlobNotInArchive("/proc/sys/net/ipv6/neigh/" +
                                        "*/base_reachable_time")
        self.assertFileGlobNotInArchive("/etc/default/grub.d/" +
                                        "50-curtin-settings.cfg")

    def test_system_cmd_collected(self):
        self.assertFileGlobInArchive("ld.so_--help")
        self.assertFileGlobInArchive("ld.so_--list-diagnostics")
        self.assertFileGlobInArchive("ld.so_--list-tunables")


class SystemScrubTest(StageTwoReportTest):
    """Ensure that environment, default and sysconfig are picked up
    and properly scrubbed

    :avocado: tags=stagetwo,scrub
    """
    sos_cmd = '-o system'
    files = [
        ('../../../tests/test_data/system_test_data', '/etc/environment'),
        ('../../../tests/test_data/system_test_data', '/etc/default/proxy'),
        ('../../../tests/test_data/system_test_data', '/etc/default/proxy1'),
    ]
    secrets_list = [
        'foouser',
        'somesecretpassword'
    ]

    def test_system_files_collected(self):
        for file in self.files:
            self.assertFileGlobInArchive(file[1])

    def test_system_scrub(self):
        for file in self.files:
            for secret in self.secrets_list:
                self.assertFileNotHasContent(file[1], secret)


class SystemScrubTestRH(StageTwoReportTest):
    """Ensure that environment, default and sysconfig are picked up
    and properly scrubbed

    :avocado: tags=stagetwo,scrub
    """
    redhat_only = True
    sos_cmd = '-o system'
    files = [
        ('../../../tests/test_data/system_test_data', '/etc/sysconfig/proxy'),
        ('../../../tests/test_data/system_test_data', '/etc/sysconfig/proxy1'),
    ]
    secrets_list = [
        'foouser',
        'somesecretpassword'
    ]

    def test_system_files_collected(self):
        for file in self.files:
            self.assertFileGlobInArchive(file[1])

    def test_system_scrub(self):
        for file in self.files:
            for secret in self.secrets_list:
                self.assertFileNotHasContent(file[1], secret)

# vim: set et ts=4 sw=4 :
