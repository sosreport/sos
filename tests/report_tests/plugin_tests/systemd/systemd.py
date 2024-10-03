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
        self.assertFileCollected("/etc/systemd")
        self.assertFileCollected("/lib/systemd/system")
        self.assertFileCollected("/lib/systemd/user")
        self.assertFileCollected("/etc/vconsole.conf")
        self.assertFileCollected("/run/systemd/generator*")
        self.assertFileCollected("/run/systemd/seats")
        self.assertFileCollected("/run/systemd/sessions")
        self.assertFileCollected("/run/systemd/system")
        self.assertFileCollected("/run/systemd/users")
        self.assertFileCollected("/etc/modules-load.d/*.conf")
        self.assertFileCollected("/etc/yum/protected.d/systemd.conf")
        self.assertFileCollected("/etc/tmpfiles.d/*.conf")
        self.assertFileCollected("/run/tmpfiles.d/*.conf")
        self.assertFileCollected("/usr/lib/tmpfiles.d/*.conf")

    def test_systemd_files_forbidden(self):
        self.assertFileGlobNotInArchive("/dev/null")

    def test_systemd_cmd_collected(self):
        self.assertFileCollected("journalctl_--list-boots")
        self.assertFileCollected("ls_-alZR_.lib.systemd")
        self.assertFileCollected("resolvectl_statistics")
        self.assertFileCollected("resolvectl_status")
        self.assertFileCollected("systemctl_list-dependencies")
        self.assertFileCollected("systemctl_list-jobs")
        self.assertFileCollected("systemctl_list-machines")
        self.assertFileCollected("systemctl_list-timers_--all")
        self.assertFileCollected("systemctl_list-unit-files")
        self.assertFileCollected("systemctl_list-units")
        self.assertFileCollected("systemctl_list-units_--all")
        self.assertFileCollected("systemctl_list-units_--failed")
        self.assertFileCollected("systemctl_show_--all")
        self.assertFileCollected("systemctl_show-environment")
        self.assertFileCollected("systemctl_show_service_--all")
        self.assertFileCollected("systemctl_status_--all")
        self.assertFileCollected("systemd-analyze")
        self.assertFileCollected("systemd-analyze_blame")
        self.assertFileCollected("systemd-analyze_dump")
        self.assertFileCollected("systemd-analyze_plot.svg")
        self.assertFileCollected("systemd-delta")
        self.assertFileCollected("systemd-inhibit_--list")
        self.assertFileCollected("timedatectl")


class SystemdScrubTest(StageTwoReportTest):
    """Ensure that system files are picked up
    and properly scrubbed

    :avocado: tags=stagetwo,scrub
    """
    sos_cmd = '-o systemd'
    files = [
        ('systemd_test_data', '/etc/systemd/system'),
        ('systemd_test_data', '/lib/systemd/system'),
        ('systemd_test_data', '/run/systemd/system'),
    ]
    secrets_list = [
        'foouser',
        'somesecretpassword'
    ]

    def test_systemd_scrub(self):
        for file in self.files:
            for secret in self.secrets_list:
                self.assertFileNotHasContent(file[1], secret)

# vim: set et ts=4 sw=4 :
