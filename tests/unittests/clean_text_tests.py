# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import io
import os
import stat
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from sos.cleaner.text import CleanTextError, SoSCleanText, sanitize_stream


ROOT = Path(__file__).resolve().parents[2]


class CleanTextTests(unittest.TestCase):
    """Run CLI cases in fresh processes, as real invocations are isolated."""

    def run_clean_text(self, content=b'', *args):
        return subprocess.run(
            [sys.executable, 'bin/sos', 'clean-text', *args],
            input=content, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=ROOT, check=False
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b'')

    def test_stdin(self):
        content = '  evidence\t\r\n\n café\r\nno final newline'.encode()
        result = self.run_clean_text(content, '-')
        self.assert_success(result)
        self.assertEqual(result.stdout, content)

    def test_default_stdin(self):
        result = self.run_clean_text(b'evidence\n')
        self.assert_success(result)
        self.assertEqual(result.stdout, b'evidence\n')

    def test_file_input(self):
        content = b'  evidence\r\n10.20.30.40\nlast line'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.txt'
            path.write_bytes(content)
            result = self.run_clean_text(b'', str(path))
            self.assertEqual(path.read_bytes(), content)
        self.assert_success(result)
        self.assertEqual(result.stdout,
                         b'  evidence\r\n172.17.0.1\nlast line')

    def test_hostname(self):
        result = self.run_clean_text(b'customerhost customerhost\n', '-',
                                     '--hostnames', 'customerhost')
        self.assert_success(result)
        self.assertEqual(result.stdout, b'host0 host0\n')

    def test_domain(self):
        result = self.run_clean_text(
            b'node.customer.example customer.example\n', '-',
            '--domains', 'customer.example'
        )
        self.assert_success(result)
        self.assertNotIn(b'customer', result.stdout)
        self.assertNotIn(b'node', result.stdout)
        self.assertIn(b'obfuscateddomain0.example', result.stdout)

    def test_ipv4(self):
        result = self.run_clean_text(b'peer=10.20.30.40\n', '-')
        self.assert_success(result)
        self.assertEqual(result.stdout, b'peer=172.17.0.1\n')

    def test_ipv6(self):
        result = self.run_clean_text(b'peer=2607:c540:8c00:3318::34\n', '-')
        self.assert_success(result)
        self.assertNotIn(b'2607:c540:8c00:3318::34', result.stdout)
        self.assertIn(b'534f:', result.stdout)

    def test_mac(self):
        result = self.run_clean_text(b'mac=12:34:56:78:90:ab\n', '-')
        self.assert_success(result)
        self.assertEqual(result.stdout, b'mac=53:4f:53:00:00:01\n')

    def test_systemd_units(self):
        units = b'user-2000048158.slice session-c33.scope'
        result = self.run_clean_text(units + b' customerhost\n', '-',
                                     '--hostnames', 'customerhost')
        self.assert_success(result)
        self.assertEqual(result.stdout, units + b' host0\n')

    def test_selinux_context(self):
        context = b'system_u:system_r:sshd_net_t:s0'
        result = self.run_clean_text(context + b' 10.20.30.40\n', '-')
        self.assert_success(result)
        self.assertEqual(result.stdout, context + b' 172.17.0.1\n')

    def test_explicit_identity_in_unit(self):
        result = self.run_clean_text(b'session-c33.scope\n', '-',
                                     '--hostnames', 'session-c33.scope')
        self.assert_success(result)
        self.assertNotIn(b'session-c33', result.stdout)

    def test_explicit_identity_in_context(self):
        result = self.run_clean_text(b'system_u:system_r:sshd_net_t:s0\n',
                                     '-', '--hostnames', 'sshd_net_t')
        self.assert_success(result)
        self.assertEqual(result.stdout, b'system_u:system_r:host0:s0\n')

    def test_unknown_names(self):
        content = b'unknownhost unknown.example alice\n'
        result = self.run_clean_text(content, '-')
        self.assert_success(result)
        self.assertEqual(result.stdout, content)

    def test_stable_replacements(self):
        line = (b'customerhost 10.20.30.40 2607:c540:8c00:3318::34 '
                b'12:34:56:78:90:ab\n')
        result = self.run_clean_text(line * 3, '-', '--hostnames',
                                     'customerhost')
        self.assert_success(result)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[1], lines[2])
        self.assertNotEqual(lines[0], line.rstrip())

    def test_private_cache_and_cleanup(self):
        script = '''
import os
import stat
import sys
from unittest.mock import patch
from sos import SoS
from sos.cleaner.mappings import SoSMap

load_entries = SoSMap.load_entries
seen = []
def check_cache(mapping):
    assert os.path.dirname(mapping.workdir) == sys.argv[1]
    assert stat.S_IMODE(os.stat(mapping.workdir).st_mode) == 0o700
    seen.append(mapping.workdir)
    return load_entries(mapping)

with patch.object(SoSMap, 'load_entries', check_cache), \\
     patch('sos.cleaner.SoSCleaner.load_map_file',
           side_effect=AssertionError('system map must not be loaded')), \\
     patch('sos.cleaner.SoSCleaner.write_map_for_config',
           side_effect=AssertionError('system map must not be written')):
    SoS(['clean-text', '-', '--tmp-dir', sys.argv[1]]).execute()
assert len(seen) == 4
assert not any(os.path.exists(path) for path in seen)
'''
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, '-c', script, directory],
                input=b'10.20.30.40\n', stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, cwd=ROOT, check=False
            )
            self.assert_success(result)
            self.assertEqual(os.listdir(directory), [])

    def test_invalid_domain(self):
        result = self.run_clean_text(b'evidence\n', '-', '--domains',
                                     'invalid')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'')
        self.assertIn(b'--domains', result.stderr)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_clean_text(b'', str(Path(directory) / 'absent'))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'')
        self.assertIn(b'sos clean-text:', result.stderr)

    def test_invalid_utf8(self):
        result = self.run_clean_text(b'10.20.30.40\nsensitive\xff\n', '-')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'')
        self.assertTrue(result.stderr)
        self.assertNotIn(b'sensitive', result.stderr)

    def test_phase_one_output_equivalence(self):
        content = (
            b'customerhost node.customer.example customer.example '
            b'10.20.30.40 2607:c540:8c00:3318::34 12:34:56:78:90:ab\r\n'
            b'user-2000048158.slice session-c33.scope '
            b'system_u:system_r:sshd_net_t:s0\n'
            + ' café\tno final newline'.encode()
        )
        # Captured from the committed phase 1 CLI before adding staging.
        expected = (
            b'host0 host1.obfuscateddomain0.example '
            b'obfuscateddomain0.example 172.17.0.1 '
            b'534f:53ff:fe00:0001::0004 53:4f:53:00:00:02\r\n'
            b'user-2000048158.slice session-c33.scope '
            b'system_u:system_r:sshd_net_t:s0\n'
            + ' café\tno final newline'.encode()
        )
        result = self.run_clean_text(content, '-', '--hostnames',
                                     'customerhost', '--domains',
                                     'customer.example')
        self.assert_success(result)
        self.assertEqual(result.stdout, expected)

    def test_parser_failure_exit_status(self):
        script = '''
from unittest.mock import patch
from sos import SoS
with patch('sos.cleaner.text.SoSIPParser.parse_line',
           side_effect=RuntimeError('sensitive input')):
    SoS(['clean-text', '-']).execute()
'''
        result = subprocess.run(
            [sys.executable, '-c', script], input=b'10.20.30.40\n',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=ROOT, check=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'')
        self.assertIn(b'IP Parser failed on line 1', result.stderr)
        self.assertNotIn(b'sensitive input', result.stderr)

    def test_failed_line_is_not_written(self):
        parser = mock.Mock(name='parser')
        parser.name = 'Test Parser'
        parser.parse_line.side_effect = [('safe\n', 1), RuntimeError()]
        destination = io.BytesIO()
        with self.assertRaisesRegex(CleanTextError, 'failed on line 2'):
            sanitize_stream(io.BytesIO(b'first\nsecond\n'), destination,
                            [parser])
        self.assertEqual(destination.getvalue(), b'safe\n')


class CleanTextStagingTests(unittest.TestCase):
    """Exercise the release boundary with real private temporary files."""

    def run_staged(self, failure=None):
        output = io.BytesIO()
        stderr = io.StringIO()
        source = io.BytesIO(b'10.20.30.40\nsensitive input\n')
        temporary_file = tempfile.NamedTemporaryFile
        seen = []

        def make_staged(*args, **kwargs):
            staged = temporary_file(*args, **kwargs)
            seen.append(staged.name)
            self.assertEqual(stat.S_IMODE(os.stat(staged.name).st_mode),
                             0o600)
            self.assertEqual(stat.S_IMODE(
                os.stat(Path(staged.name).parent).st_mode), 0o700)
            if failure in ('write', 'flush', 'seek'):
                original = getattr(staged, failure)

                def fail_once(*args, **kwargs):
                    # Restore so cleanup itself can flush and close normally.
                    setattr(staged, failure, original)
                    raise OSError('sensitive input')

                setattr(staged, failure, fail_once)
            return staged

        calls = []

        def parse_line(line):
            self.assertEqual(output.getvalue(), b'')
            calls.append(line)
            if len(calls) == 2 and failure == 'parser':
                raise RuntimeError(line)
            return 'sanitized\n', 1

        def failing_input():
            yield b'10.20.30.40\n'
            raise OSError('sensitive input')

        if failure == 'input':
            source = failing_input()
        elif failure == 'decoding':
            source = io.BytesIO(b'10.20.30.40\nsensitive input\xff\n')

        with tempfile.TemporaryDirectory() as directory:
            opts = SimpleNamespace(domains=[], hostnames=[], target='-',
                                   tmp_dir=directory)
            command = SoSCleanText(None, opts, None)
            with mock.patch('sos.cleaner.text.sys.stdin', buffer=source), \
                    mock.patch('sos.cleaner.text.sys.stdout', buffer=output), \
                    mock.patch('sos.cleaner.text.sys.stderr', stderr), \
                    mock.patch('sos.cleaner.text.tempfile.NamedTemporaryFile',
                               side_effect=make_staged), \
                    mock.patch('sos.cleaner.text.SoSIPParser.parse_line',
                               side_effect=parse_line):
                if failure:
                    with self.assertRaises(SystemExit) as raised:
                        command.execute()
                    self.assertNotEqual(raised.exception.code, 0)
                    self.assertEqual(output.getvalue(), b'')
                    self.assertTrue(stderr.getvalue())
                    self.assertNotIn('sensitive input', stderr.getvalue())
                    if failure == 'parser':
                        self.assertIn('failed on line 2', stderr.getvalue())
                else:
                    command.execute()
                    self.assertEqual(output.getvalue(),
                                     b'sanitized\nsanitized\n')
                    self.assertEqual(stderr.getvalue(), '')
            self.assertEqual(len(seen), 1)
            self.assertFalse(os.path.exists(seen[0]))
            self.assertEqual(os.listdir(directory), [])

    def test_success_removes_private_output(self):
        self.run_staged()

    def test_line_two_parser_failure_removes_output(self):
        self.run_staged('parser')

    def test_line_two_decoding_failure_removes_output(self):
        self.run_staged('decoding')

    def test_line_two_input_failure_removes_output(self):
        self.run_staged('input')

    def test_output_preparation_failure_removes_output(self):
        for operation in ('write', 'flush', 'seek'):
            with self.subTest(operation=operation):
                self.run_staged(operation)
