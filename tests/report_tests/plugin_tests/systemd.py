# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest, StageTwoReportTest


class SystemdPluginTest(StageOneReportTest):
    """Basic sanity check to make sure common config files are collected

    :avocado: tags=stageone
    """

    sos_cmd = '-o systemd'

    def test_systemd_files_collected(self):
        self.assertFileGlobInArchive("/etc/systemd")
        self.assertFileGlobInArchive("/lib/systemd/system")
        self.assertFileGlobInArchive("/lib/systemd/user")
        self.assertFileGlobInArchive("/etc/vconsole.conf")
        self.assertFileGlobInArchive("/run/systemd/generator*")
        self.assertFileGlobInArchive("/run/systemd/seats")
        self.assertFileGlobInArchive("/run/systemd/sessions")
        self.assertFileGlobInArchive("/run/systemd/system")
        self.assertFileGlobInArchive("/run/systemd/users")
        self.assertFileGlobInArchive("/etc/modules-load.d/*.conf")
        self.assertFileGlobInArchive("/etc/yum/protected.d/systemd.conf")
        self.assertFileGlobInArchive("/etc/tmpfiles.d/*.conf")
        self.assertFileGlobInArchive("/run/tmpfiles.d/*.conf")
        self.assertFileGlobInArchive("/usr/lib/tmpfiles.d/*.conf")

    def test_systemd_files_forbidden(self):
        self.assertFileGlobNotInArchive("/dev/null")

    def test_systemd_cmd_collected(self):
        self.assertFileGlobInArchive("journalctl_--list-boots")
        self.assertFileGlobInArchive("ls_-alZR_.lib.systemd")
        self.assertFileGlobInArchive("resolvectl_statistics")
        self.assertFileGlobInArchive("resolvectl_status")
        self.assertFileGlobInArchive("systemctl_list-dependencies")
        self.assertFileGlobInArchive("systemctl_list-jobs")
        self.assertFileGlobInArchive("systemctl_list-machines")
        self.assertFileGlobInArchive("systemctl_list-timers_--all")
        self.assertFileGlobInArchive("systemctl_list-unit-files")
        self.assertFileGlobInArchive("systemctl_list-units")
        self.assertFileGlobInArchive("systemctl_list-units_--all")
        self.assertFileGlobInArchive("systemctl_list-units_--failed")
        self.assertFileGlobInArchive("systemctl_show_--all")
        self.assertFileGlobInArchive("systemctl_show-environment")
        self.assertFileGlobInArchive("systemctl_show_service_--all")
        self.assertFileGlobInArchive("systemctl_status_--all")
        self.assertFileGlobInArchive("systemd-analyze")
        self.assertFileGlobInArchive("systemd-analyze_blame")
        self.assertFileGlobInArchive("systemd-analyze_dump")
        self.assertFileGlobInArchive("systemd-analyze_plot.svg")
        self.assertFileGlobInArchive("systemd-delta")
        self.assertFileGlobInArchive("systemd-inhibit_--list")
        self.assertFileGlobInArchive("timedatectl")


class SystemdScrubTest(StageTwoReportTest):
    """Ensure that system files are picked up
    and properly scrubbed

    :avocado: tags=stagetwo,scrub
    """
    sos_cmd = '-o systemd'
    files = [
        ('../../../tests/test_data/system_test_data', '/etc/systemd/system'),
        ('../../../tests/test_data/system_test_data', '/lib/systemd/system'),
        ('../../../tests/test_data/system_test_data', '/run/systemd/system'),
    ]
    secrets_list = [
        'foouser',
        'somesecretpassword'
    ]

    def test_systemd_files_collected(self):
        for file in self.files:
            self.assertFileGlobInArchive(file[1])

    def test_systemd_scrub(self):
        for file in self.files:
            for secret in self.secrets_list:
                self.assertFileNotHasContent(file[1], secret)

# vim: set et ts=4 sw=4 :
