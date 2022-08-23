# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest, StageTwoReportTest


ARCHIVE = 'sosreport-cleanertest-2021-08-03-qpkxdid.tar.xz'

class ReportDisabledParsersTest(StageOneReportTest):
    """Run report with selected disabled parsers and ensure those parsers are
    in fact disabled and unused.

    :avocado: tags=stageone
    """

    sos_cmd = '--clean -o host,kernel,networking --disable-parsers=ip'

    def test_local_ip_not_obfuscated(self):
        self.assertFileHasContent('ip_addr', self.sysinfo['pre']['networking']['ip_addr'])

    def test_disable_message_logged(self):
        self.assertSosLogContains('Disabling parser: ip')

    def test_ui_log_message_shown(self):
        self.assertSosUILogContains(
            '.*Be aware that this may leave sensitive plain-text data in the archive.'
        )

    # make sure that the other parsers remain functional
    def test_localhost_was_obfuscated(self):
        self.assertFileHasContent('hostname', 'host0')

    def test_mac_addrs_were_obfuscated(self):
        content = self.get_file_content('sos_commands/networking/ip_maddr_show')
        for line in content.splitlines():
            if line.strip().startswith('link'):
                mac = line.strip().split()[1]
                assert mac.startswith('53:4f:53'), "Found unobfuscated mac addr %s" % mac


class NativeCleanDisabledParsersTest(StageTwoReportTest):
    """Ensure that disabling parsers works when calling 'clean' directly as
    well.

    :avocado: tags=stagetwo
    """

    sos_cmd = "--disable-parsers=hostname tests/test_data/%s" % ARCHIVE
    sos_component = 'clean'

    def test_localhost_not_obfuscated(self):
        self.assertFileNotHasContent('hostname', self.sysinfo['pre']['networking']['hostname'])
        self.assertFileNotHasContent('uname', self.sysinfo['pre']['networking']['hostname'])

    def test_local_ip_was_obfuscated(self):
        self.assertFileNotHasContent('ip_addr', self.sysinfo['pre']['networking']['ip_addr'])
