# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from avocado.utils import process
from sos_tests import StageOneReportTest


class EncryptedReportTest(StageOneReportTest):
    """Tests the use of --encrypt-pass to ensure that the archive is
    successfully encrypted.

    :avocado: tags=stageone
    """

    encrypt_pass = 'sostest'
    sos_cmd = "-o kernel --encrypt-pass %s" % encrypt_pass

    def test_archive_gpg_encrypted(self):
        self.assertOutputContains('/.*sosreport-.*tar.*\.gpg')
        _cmd = "file %s" % self.encrypted_path
        res = process.run(_cmd)
        self.assertTrue("GPG symmetrically encrypted data" in res.stdout.decode())

    def test_tarball_named_secure(self):
        self.assertTrue('secured-' in self.encrypted_path)


class EncryptedCleanedReportTest(EncryptedReportTest):
    """Ensure that we can successfully both encrypt and clean a report in a
    single execution

    :avocado: tags=stageone
    """

    encrypt_pass = 'sostest'
    sos_cmd = "-o host,networking --clean --encrypt-pass %s" % encrypt_pass

    def test_hostname_obfuscated(self):
        self.assertFileHasContent('hostname', 'host0')

    def test_tarball_named_obfuscated(self):
        self.assertTrue('obfuscated' in self.archive)

    def test_ip_address_was_obfuscated(self):
        self.assertFileNotHasContent('ip_addr', self.sysinfo['pre']['networking']['ip_addr'])
