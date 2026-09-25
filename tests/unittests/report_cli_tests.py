import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock

from sos import SoS
from sos.cleaner.report_residual import ReportTreeResidualError
from sos.cleaner.sanitizer import ReportSanitizerError


ROOT = Path(__file__).resolve().parents[2]


class ReportCliTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        self.tree = self.root / 'tree'
        self.tree.mkdir()
        self.archive = self.root / 'input.tar.xz'
        self.output = self.root / 'output.tar.xz'

    def tearDown(self):
        self.work.cleanup()

    def write(self, relative, content):
        path = self.tree / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def make_archive(self):
        with tarfile.open(self.archive, 'w:xz') as archive:
            archive.add(self.tree, arcname='report')

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, 'bin/sos', 'sanitize-report', *args],
            cwd=ROOT, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False)

    def populate(self):
        self.write('hostname', 'node.example.invalid\n')
        self.write('etc/hosts', '192.0.2.44 node.example.invalid node\n')
        self.write('sos_commands/networking/ip_-o_addr',
                   'inet 192.0.2.44 inet6 2001:db8::44 '
                   'link/ether 12:34:56:78:90:ab\n')
        self.write('var/log/auth.log', 'acct="alice"\n')
        self.write('details', 'node.example.invalid alice@example.invalid '
                   'password=SyntheticSecret123\n')

    def test_help_and_required_options(self):
        result = subprocess.run(
            [sys.executable, 'bin/sos', 'sanitize-report', '--help'],
            cwd=ROOT, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertIn('sanitize-report', result.stdout)
        self.assertIn('--mapping-output', result.stdout)
        self.assertIn('private correlation', result.stdout)

        missing_input = self.run_cli('--output', str(self.output))
        self.assertNotEqual(missing_input.returncode, 0)
        self.assertNotIn('Traceback', missing_input.stderr)

        missing_output = self.run_cli(str(self.archive))
        self.assertNotEqual(missing_output.returncode, 0)

    def test_basic_success_has_no_mapping_by_default(self):
        self.populate()
        self.make_archive()
        result = self.run_cli(str(self.archive), '--output', str(self.output),
                              '--domain', 'example.invalid', '--username',
                              'alice')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.output.exists())
        self.assertIn('Mapping file written: no', result.stdout)
        self.assertNotIn('node.example.invalid', result.stdout)
        self.assertFalse((self.root / 'mapping.json').exists())

    def test_explicit_mapping_is_private_and_separate(self):
        self.populate()
        self.make_archive()
        mapping = self.root / 'private-map.json'
        result = self.run_cli(str(self.archive), '--output', str(self.output),
                              '--mapping-output', str(mapping), '--domain',
                              'example.invalid', '--username', 'alice',
                              '--hostname', 'node')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(mapping.stat().st_mode & 0o777, 0o600)
        data = json.loads(mapping.read_text(encoding='utf-8'))
        self.assertEqual(data['hostnames']['node'], 'host0')
        with tarfile.open(self.output, 'r:xz') as archive:
            self.assertNotIn(mapping.name, [member.name for member in archive])

    def test_collisions_and_existing_outputs_are_rejected(self):
        self.populate()
        self.make_archive()
        mapping = self.root / 'mapping.json'
        for output, map_path in ((self.archive, None),
                                 (self.output, self.output),
                                 (self.output, self.archive)):
            if output == self.output and output.exists():
                output.unlink()
            result = self.run_cli(str(self.archive), '--output', str(output),
                                  *(('--mapping-output', str(map_path))
                                    if map_path else ()))
            self.assertNotEqual(result.returncode, 0)
        self.output.write_bytes(b'keep')
        result = self.run_cli(str(self.archive), '--output', str(self.output))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_bytes(), b'keep')

    def test_malicious_and_unsupported_inputs_fail_without_sensitive_errors(self):
        bad = self.root / 'bad.tar.xz'
        bad.write_bytes(b'not an archive')
        result = self.run_cli(str(bad), '--output', str(self.output))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr)
        self.assertNotIn(str(bad), result.stderr)

    def test_sanitizer_failure_remains_generic(self):
        self.tree.joinpath('opaque').write_bytes(b'unknown\x00binary')
        self.make_archive()
        result = self.run_cli(str(self.archive), '--output',
                              str(self.output))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            result.stderr,
            'sos sanitize-report: ERROR: report sanitization failed\n')
        self.assertNotIn('Traceback', result.stderr)

    def test_cli_hides_safe_internal_residual_context(self):
        error = ReportSanitizerError({})
        error.__cause__ = ReportTreeResidualError(
            {}, 'known hostname', ('safe', 'details.txt'))
        self.make_archive()
        command = SoS(['sanitize-report', str(self.archive), '--output',
                       str(self.output)])
        stderr = StringIO()
        with mock.patch('sos.cleaner.report_cli.ReportSanitizer.sanitize',
                        side_effect=error), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as context:
                command.execute()
        self.assertEqual(context.exception.code, 1)
        self.assertEqual(
            stderr.getvalue(),
            'sos sanitize-report: ERROR: report sanitization failed\n')
        self.assertNotIn('details.txt', stderr.getvalue())

    def test_keyboard_interrupt_is_nonzero_and_does_not_publish(self):
        self.populate()
        self.make_archive()
        command = SoS(['sanitize-report', str(self.archive),
                       '--output', str(self.output)])
        stderr = StringIO()
        with mock.patch('sos.cleaner.report_cli.ReportSanitizer.sanitize',
                        side_effect=KeyboardInterrupt), \
                redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as context:
                command.execute()
        self.assertEqual(context.exception.code, 130)
        self.assertFalse(self.output.exists())
        self.assertIn('interrupted', stderr.getvalue())

    def test_repeatable_and_comma_separated_seeds(self):
        self.populate()
        self.make_archive()
        result = self.run_cli(str(self.archive), '--output', str(self.output),
                              '--hostname', 'node,other', '--domain',
                              'example.invalid', '--username', 'alice',
                              '--username', 'other')
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
