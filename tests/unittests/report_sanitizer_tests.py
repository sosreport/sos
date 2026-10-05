import io
import os
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sos.cleaner.archiver import SafeReportArchiverError
from sos.cleaner.sanitizer import ReportSanitizer, ReportSanitizerError
from sos.cleaner.tree import ReportTreeSanitizerError
from sos.cleaner.report_residual import ReportTreeResidualError


class ReportSanitizerTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        self.input_tree = self.root / 'input-tree'
        self.input_tree.mkdir()
        self.output = self.root / 'sanitized.tar.xz'

    def tearDown(self):
        self.work.cleanup()

    def write(self, name, content):
        path = self.input_tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def make_archive(self, name='input.tar.xz'):
        path = self.root / name
        with tarfile.open(path, 'w:xz') as archive:
            archive.add(self.input_tree, arcname='sosreport-input')
        return path

    def populate_realistic_tree(self):
        self.write('hostname', 'db-prod-01.customer.example\n')
        self.write('etc/hosts',
                   '10.20.30.40 db-prod-01.customer.example db-prod-01\n')
        self.write('sos_commands/networking/ip_-o_addr',
                   '2: eth0 inet 10.20.30.40/24 '
                   'inet6 2001:db8::10/64 '
                   'link/ether 12:34:56:78:90:ab\n')
        self.write('var/log/auth.log', 'audit: acct="alice" AUID="alice"\n')
        self.write('details.txt',
                   'db-prod-01.customer.example 10.20.30.40 '
                   '2001:db8::10 12:34:56:78:90:ab '
                   'alice@customer.example acct="alice"\n'
                   'password=SuperSecret123\n'
                   'Authorization: Bearer synthetic-token\n'
                   'system_u:system_r:sshd_net_t:s0\n'
                   'systemd-user.slice package-1.2.3\n')

    def run_pipeline(self, **kwargs):
        archive = self.make_archive()
        mapping_output = kwargs.pop('mapping_output', None)
        result = ReportSanitizer(temp_parent=self.root, **kwargs).sanitize(
            archive, self.output, mapping_output=mapping_output)
        return archive, result

    def test_complete_pipeline_and_canonical_output(self):
        self.populate_realistic_tree()
        archive, result = self.run_pipeline(
            domains=('customer.example',), usernames=('alice',))
        self.assertTrue(self.output.exists())
        self.assertGreater(result['archive']['members_written'], 0)
        self.assertGreater(result['discovered']['hostnames'], 0)

        input_bytes = archive.read_bytes()
        with tarfile.open(self.output, 'r:xz') as sanitized:
            members = sanitized.getmembers()
            names = [member.name for member in members]
            contents = []
            for member in members:
                self.assertFalse(member.name.startswith('/'))
                self.assertNotIn('..', member.name.split('/'))
                self.assertEqual((member.uid, member.gid), (0, 0))
                self.assertEqual((member.uname, member.gname), ('', ''))
                self.assertEqual(member.mtime, 0)
                self.assertEqual(member.pax_headers, {})
                if member.isfile():
                    contents.append(sanitized.extractfile(member).read())
            data = b'\n'.join(contents)
        for original in (b'db-prod-01', b'customer.example',
                         b'10.20.30.40', b'2001:db8::10',
                         b'12:34:56:78:90:ab', b'alice@customer.example',
                         b'acct="alice"'):
            self.assertNotIn(original, data)
        self.assertNotIn(b'SuperSecret123', data)
        self.assertNotIn(b'Bearer synthetic-token', data)
        self.assertIn(b'[REDACTED_SECRET]', data)
        self.assertIn(b'[REDACTED_TOKEN]', data)
        self.assertIn(b'system_u:system_r:sshd_net_t:s0', data)
        self.assertIn(b'systemd-user.slice', data)
        self.assertIn(b'package-1.2.3', data)
        self.assertEqual(archive.read_bytes(), input_bytes)

    def test_failures_publish_no_output(self):
        archive = self.root / 'malformed.tar.xz'
        archive.write_bytes(b'not a tar archive')
        with self.assertRaises(ReportSanitizerError):
            ReportSanitizer(temp_parent=self.root).sanitize(
                archive, self.output)
        self.assertFalse(self.output.exists())

        self.populate_realistic_tree()
        archive = self.make_archive('realistic.tar.xz')
        with mock.patch('sos.cleaner.sanitizer.ReportIdentityDiscovery.discover',
                        side_effect=RuntimeError):
            with self.assertRaises(ReportSanitizerError):
                ReportSanitizer(temp_parent=self.root).sanitize(
                    archive, self.output)
        self.assertFalse(self.output.exists())

        with mock.patch('sos.cleaner.sanitizer.SafeReportArchiver.create_private',
                        side_effect=SafeReportArchiverError({})):
            with self.assertRaises(ReportSanitizerError):
                ReportSanitizer(temp_parent=self.root).sanitize(
                    archive, self.output)
        self.assertFalse(self.output.exists())

    def test_unsupported_binary_publishes_neither_output_nor_mapping(self):
        binary = self.input_tree / 'opaque.txt'
        binary.write_bytes(b'unknown\x00binary')
        source = binary.read_bytes()
        archive = self.make_archive('binary.tar.xz')
        mapping = self.root / 'binary-map.json'

        with self.assertRaises(ReportSanitizerError):
            ReportSanitizer(temp_parent=self.root).sanitize(
                archive, self.output, mapping_output=mapping)

        self.assertFalse(self.output.exists())
        self.assertFalse(mapping.exists())
        self.assertEqual(binary.read_bytes(), source)

    def test_public_apt_keyring_is_omitted_from_final_archive(self):
        keyring = bytes((0x98, 22)) + b'\x04\x00synthetic-public-key'
        keyring_path = self.input_tree / 'etc/apt/trusted.gpg.d/synthetic.gpg'
        keyring_path.parent.mkdir(parents=True, exist_ok=True)
        keyring_path.write_bytes(keyring)
        archive = self.make_archive('keyring.tar.xz')

        result = ReportSanitizer(temp_parent=self.root).sanitize(
            archive, self.output)

        self.assertEqual(result['tree']['package_keyrings_omitted'], 1)
        with tarfile.open(self.output, 'r:xz') as output:
            self.assertNotIn(
                'sosreport-input/etc/apt/trusted.gpg.d/synthetic.gpg',
                [member.name for member in output])

    def test_unreadable_regular_file_is_inspected_and_readable_in_output(self):
        path = self.input_tree / 'details/unreadable.log'
        path.parent.mkdir(parents=True, exist_ok=True)
        content = b'node\npassword=SyntheticSecret123\n'
        path.write_bytes(content)
        write_only_content = b'alice\npassword=SyntheticSecret456\n'
        write_only = self.input_tree / 'details/write-only.log'
        write_only.write_bytes(write_only_content)
        archive = self.root / 'unreadable.tar.xz'
        with tarfile.open(archive, 'w:xz') as output:
            for name, data, mode in (
                    ('unreadable.log', content, 0o000),
                    ('write-only.log', write_only_content, 0o200)):
                info = tarfile.TarInfo('sosreport-input/details/' + name)
                info.mode = mode
                info.size = len(data)
                output.addfile(info, io.BytesIO(data))
        path.chmod(0o000)
        write_only.chmod(0o200)
        before_mode = path.stat().st_mode

        result = ReportSanitizer(hostnames=('node',), usernames=('alice',),
                                 temp_parent=self.root) \
            .sanitize(archive, self.output)

        self.assertGreater(result['tree']['text_files_sanitized'], 0)
        self.assertEqual(path.stat().st_mode, before_mode)
        with tarfile.open(self.output, 'r:xz') as output:
            member = output.getmember('sosreport-input/details/unreadable.log')
            self.assertEqual(member.mode, 0o400)
            content = output.extractfile(member).read()
            write_only_member = output.getmember(
                'sosreport-input/details/write-only.log')
            self.assertEqual(write_only_member.mode, 0o600)
            write_only_content = output.extractfile(write_only_member).read()
        self.assertNotIn(b'node\n', content)
        self.assertNotIn(b'SyntheticSecret123', content)
        self.assertNotIn(b'alice\n', write_only_content)
        self.assertNotIn(b'SyntheticSecret456', write_only_content)

    def test_residual_failure_and_existing_output_are_fail_closed(self):
        self.populate_realistic_tree()
        archive = self.make_archive()
        with mock.patch('sos.cleaner.sanitizer.ReportTreeSanitizer.sanitize',
                        side_effect=ReportTreeSanitizerError({})):
            with self.assertRaises(ReportSanitizerError) as context:
                ReportSanitizer(temp_parent=self.root).sanitize(
                    archive, self.output)
        self.assertIsInstance(context.exception.__cause__,
                              ReportTreeSanitizerError)
        self.assertFalse(self.output.exists())

        self.output.write_bytes(b'keep')
        with self.assertRaises(ReportSanitizerError):
            ReportSanitizer(temp_parent=self.root).sanitize(
                archive, self.output)
        self.assertEqual(self.output.read_bytes(), b'keep')

    def test_safe_residual_cause_is_preserved_without_sensitive_values(self):
        residual = ReportTreeResidualError(
            {}, 'known hostname', ('safe', 'details.txt'))
        cause = ReportTreeSanitizerError({})
        cause.__cause__ = residual
        self.populate_realistic_tree()
        archive = self.make_archive('residual-cause.tar.xz')
        with mock.patch('sos.cleaner.sanitizer.ReportTreeSanitizer.sanitize',
                        side_effect=cause):
            with self.assertRaises(ReportSanitizerError) as context:
                ReportSanitizer(temp_parent=self.root).sanitize(
                    archive, self.output)
        chain = context.exception.__cause__
        self.assertIsInstance(chain, ReportTreeSanitizerError)
        self.assertIs(chain.__cause__, residual)
        self.assertEqual(chain.__cause__.category, 'known hostname')
        self.assertEqual(chain.__cause__.relative_path,
                         ('safe', 'details.txt'))
        self.assertNotIn('node', str(context.exception))
        self.assertNotIn('secret', str(context.exception))

    def test_cleanup_removes_private_intermediates(self):
        self.populate_realistic_tree()
        archive = self.make_archive()
        self.run_pipeline(domains=('customer.example',), usernames=('alice',))
        leftovers = [path for path in self.root.iterdir()
                     if path.name.startswith('.sos-report-sanitize-')]
        self.assertEqual(leftovers, [])

    def test_explicit_mapping_is_separate_from_archive(self):
        self.populate_realistic_tree()
        mapping = self.root / 'private-mapping.json'
        archive, result = self.run_pipeline(
            domains=('customer.example',), usernames=('alice',),
            mapping_output=mapping)
        self.assertTrue(mapping.exists())
        self.assertTrue(result['mapping_written'])
        self.assertEqual(mapping.stat().st_mode & 0o777, 0o600)
        with tarfile.open(self.output, 'r:xz') as output:
            self.assertNotIn(mapping.name, [member.name for member in output])
        self.assertNotIn(b'SuperSecret123', mapping.read_bytes())

    def test_mapping_collisions_and_compensation_are_fail_closed(self):
        self.populate_realistic_tree()
        archive = self.make_archive()
        mapping = self.root / 'private-mapping.json'
        with self.assertRaises(ReportSanitizerError):
            ReportSanitizer(temp_parent=self.root).sanitize(
                archive, self.output, mapping_output=archive)
        with self.assertRaises(ReportSanitizerError):
            ReportSanitizer(temp_parent=self.root).sanitize(
                archive, self.output, mapping_output=self.output)

        with mock.patch('sos.cleaner.sanitizer.MappingManifestWriter.write',
                        side_effect=RuntimeError):
            with self.assertRaises(ReportSanitizerError):
                ReportSanitizer(temp_parent=self.root).sanitize(
                    archive, self.output, mapping_output=mapping)
        self.assertFalse(self.output.exists())
        self.assertFalse(mapping.exists())


if __name__ == '__main__':
    unittest.main()
