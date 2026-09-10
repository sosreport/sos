import os
import stat
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.report_residual import (ReportTreeResidualError,
                                         ReportTreeResidualValidator)
from sos.cleaner.session import SanitizationSession
from sos.cleaner.tree import ReportTreeSanitizer, ReportTreeSanitizerError


class ReportResidualTests(unittest.TestCase):
    def setUp(self):
        self.source_dir = tempfile.TemporaryDirectory()
        self.work_dir = tempfile.TemporaryDirectory()
        self.output_dir = tempfile.TemporaryDirectory()
        self.source = Path(self.source_dir.name)
        self.session = SanitizationSession(
            self.work_dir.name, hostnames=('node',),
            domains=('customer.example',), usernames=('alice',))
        self.session.sanitize_line(
            'node customer.example 10.20.30.40 2001:db8::10 '
            '12:34:56:78:90:ab alice alice@example.test')
        self.manifest = SoSMappingManifest.from_session(self.session)

    def tearDown(self):
        self.output_dir.cleanup()
        self.work_dir.cleanup()
        self.source_dir.cleanup()

    def write(self, name, value):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding='utf-8')
        return path

    def assert_rejected(self, relative, value):
        self.write(relative, value)
        with self.assertRaises(ReportTreeResidualError):
            ReportTreeResidualValidator(self.source, self.manifest).validate()

    def test_known_originals_in_all_object_text_are_rejected(self):
        cases = (
            ('host.txt', 'node'), ('customer.example', 'x'),
            ('ipv4.txt', '10.20.30.40'),
            ('ipv6.txt', '2001:db8::10'),
            ('mac.txt', '12:34:56:78:90:ab'),
            ('email.txt', 'alice@example.test'), ('user.txt', 'alice'),
        )
        for relative, value in cases:
            with self.subTest(value=value):
                self.assert_rejected(relative, value)
                (self.source / relative).unlink()

    def test_original_in_filename_directory_and_symlink_target(self):
        directory = self.source / 'node'
        directory.mkdir()
        self.write('node/file', 'safe\n')
        with self.assertRaises(ReportTreeResidualError):
            ReportTreeResidualValidator(self.source, self.manifest).validate()

        for path in (directory / 'file', directory):
            if path.is_dir():
                for child in path.iterdir():
                    child.unlink()
                path.rmdir()
            elif path.exists():
                path.unlink()
        self.write('safe', 'safe\n')
        (self.source / 'link').symlink_to('node')
        with self.assertRaises(ReportTreeResidualError):
            ReportTreeResidualValidator(self.source, self.manifest).validate()

    def test_generated_aliases_are_allowed_and_clean_tree_passes(self):
        self.write('node.txt', 'node\n')
        output = Path(self.output_dir.name) / 'clean'
        ReportTreeSanitizer(self.source, output, self.session).sanitize()
        result = ReportTreeResidualValidator(
            output, SoSMappingManifest.from_session(self.session)).validate()
        self.assertEqual(result['residual_failures'], 0)

    def test_generic_secret_residuals_are_rejected_but_markers_allowed(self):
        for value in (
                'Bearer unresolved-token',
                'eyJheader.payload.signature',
                'AKIASYNTHETIC0000000',
                '-----BEGIN PRIVATE KEY-----',
                'password=unresolved'):
            with self.subTest(value=value):
                self.assert_rejected('secret.txt', value)
                (self.source / 'secret.txt').unlink()
        self.write('approved.txt',
                   '[REDACTED_SECRET] [REDACTED_TOKEN] '
                   '[REDACTED_PRIVATE_KEY]\n')
        self.assertEqual(
            ReportTreeResidualValidator(self.source, self.manifest).validate()
            ['residual_failures'], 0)

    def test_unsupported_object_fails_and_does_not_publish(self):
        os.mkfifo(self.source / 'pipe')
        destination = Path(self.output_dir.name) / 'published'
        with self.assertRaises(ReportTreeSanitizerError):
            ReportTreeSanitizer(self.source, destination,
                                self.session).sanitize()
        self.assertFalse(destination.exists())

    def test_manifest_and_diagnostics_do_not_expose_values(self):
        before = self.manifest.raw_mappings()
        self.write('residual.txt', 'node\n')
        with self.assertRaises(ReportTreeResidualError) as context:
            ReportTreeResidualValidator(self.source, self.manifest).validate()
        self.assertNotIn('node', str(context.exception))
        self.assertEqual(before, self.manifest.raw_mappings())


if __name__ == '__main__':
    unittest.main()
