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


class CleanTextSecretTests(unittest.TestCase):
    """All credentials below are synthetic and have no external validity."""

    run_clean_text = CleanTextTests.run_clean_text

    def check_redaction(self, content, expected, secrets):
        result = self.run_clean_text(content.encode(), '-')
        # Boolean assertions avoid echoing credential contents on failure.
        self.assertTrue(result.returncode == 0)
        self.assertTrue(result.stderr == b'')
        self.assertTrue(result.stdout == expected.encode())
        for value in secrets:
            self.assertFalse(value.encode() in result.stdout)
            self.assertFalse(value.encode() in result.stderr)

    def test_secret_assignments(self):
        for key in ('password', 'passwd', 'pwd', 'secret', 'api_key',
                    'api-key', 'apikey', 'DB_PASSWORD', '--password'):
            with self.subTest(key=key):
                value = 'synthetic-credential-value'
                self.check_redaction(key + '=' + value + '\n',
                                     key + '=[REDACTED_SECRET]\n', [value])
        self.check_redaction('token: synthetic-token-value\n',
                             'token: [REDACTED_TOKEN]\n',
                             ['synthetic-token-value'])

    def test_quoted_and_multiline_assignments(self):
        self.check_redaction(
            '\"password\": \"synthetic \\\"quoted\\\"\n'
            'continued\", other=ok\r\n',
            '\"password\": \"[REDACTED_SECRET]\n\", other=ok\r\n',
            ['synthetic', 'continued'])
        self.check_redaction("passwd='synthetic unfinished\nremainder",
                             "passwd='[REDACTED_SECRET]\n",
                             ['synthetic', 'remainder'])

    def test_bearer(self):
        self.check_redaction('Authorization: Bearer '
                             'synthetic.bearer/value==\n',
                             'Authorization: Bearer [REDACTED_TOKEN]\n',
                             ['synthetic.bearer/value=='])
        self.check_redaction('token=Bearer synthetic-bearer\n',
                             'token=[REDACTED_TOKEN]\n', ['synthetic-bearer'])

    def test_jwt(self):
        value = 'eyJzeW50aGV0aWMiOnRydWV9.eyJ0ZXN0Ijp0cnVlfQ.c3ludGhldGlj'
        self.check_redaction('jwt ' + value, 'jwt [REDACTED_TOKEN]', [value])

    def test_aws_ids(self):
        for prefix in ('AKIA', 'ASIA'):
            value = prefix + 'SYNTHETIC0000000'
            self.check_redaction('id ' + value,
                                 'id [REDACTED_SECRET]', [value])

    def test_private_keys(self):
        for kind in ('PRIVATE KEY', 'RSA PRIVATE KEY', 'EC PRIVATE KEY',
                     'DSA PRIVATE KEY', 'ENCRYPTED PRIVATE KEY',
                     'OPENSSH PRIVATE KEY'):
            with self.subTest(kind=kind):
                self.check_redaction(
                    'before -----BEGIN ' + kind + '-----\r\n'
                    'synthetic-key-body\r\n-----END ' + kind + '----- after\n',
                    'before [REDACTED_PRIVATE_KEY]\r\n\r\n after\n',
                    ['synthetic-key-body'])
        self.check_redaction('-----BEGIN PRIVATE KEY-----\ntruncated-body',
                             '[REDACTED_PRIVATE_KEY]\n', ['truncated-body'])

    def test_url_credentials(self):
        self.check_redaction(
            'https://synthetic-user:synthetic%40password@example.test/path\n',
            'https://[REDACTED_SECRET]@example.test/path\n',
            ['synthetic-user', 'synthetic%40password'])

    def test_false_positives(self):
        content = (
            'system_u:system_r:sshd_net_t:s0\n'
            'user-2000048158.slice session-c33.scope\n'
            'passwd shadow-utils python3-secretstorage api-key-tools\n'
            'sha256=0123456789abcdef0123456789abcdef\n'
            '550e8400-e29b-41d4-a716-446655440000\n'
            'cat /etc/passwd; pwd; systemctl status sshd.service\n'
            'password-file=/etc/example token_count=3 tokenizer=ok\n'
            'alice https://example.test/path\n'
            '-----BEGIN CERTIFICATE-----\nsynthetic-public-body\n'
            '-----END CERTIFICATE-----\n'
        )
        self.check_redaction(content, content, [])

    def test_secrets_cannot_reach_maps_or_cache(self):
        from sos.cleaner.mappings import SoSMap
        from sos.cleaner.parsers.ip_parser import SoSIPParser
        from sos.cleaner.parsers.ipv6_parser import SoSIPv6Parser
        from sos.cleaner.parsers.mac_parser import SoSMacParser
        from sos.cleaner.parsers.hostname_parser import SoSHostnameParser

        secrets = ['10.29.38.47', '2607:c540:8c00:3318::34',
                   '12:34:56:78:90:ab', 'synthetic-private-body',
                   'synthetic-api-value', 'synthetic-bearer-value',
                   'eyJzeW50aGV0aWMifQ.eyJ0ZXN0Ijp0cnVlfQ.c3ludGhldGlj',
                   'AKIASYNTHETIC0000000', 'ASIASYNTHETIC0000000',
                   'synthetic-url-password']
        source = ('password=' + secrets[0] + '\nsecret=' + secrets[1]
                  + '\ntoken=' + secrets[2] + '\n'
                  '-----BEGIN PRIVATE KEY-----\n' + secrets[3]
                  + '\n-----END PRIVATE KEY-----\n'
                  + 'api_key=' + secrets[4] + '\nBearer ' + secrets[5]
                  + '\n' + '\n'.join(secrets[6:9]) + '\n'
                  + 'https://example:' + secrets[9] + '@example.test/\n')
        original_add = SoSMap.add

        def check_add(mapping, value):
            self.assertFalse(any(secret in value for secret in secrets))
            return original_add(mapping, value)

        with tempfile.TemporaryDirectory() as directory:
            parsers = [cls({}, directory) for cls in
                       (SoSHostnameParser, SoSIPParser, SoSIPv6Parser,
                        SoSMacParser)]
            output = io.BytesIO()
            with mock.patch.object(SoSMap, 'add', check_add):
                sanitize_stream(io.BytesIO(source.encode()), output, parsers)
            for parser in parsers:
                self.assertFalse(any(secret in repr(parser.mapping.dataset)
                                     for secret in secrets))
            for path in Path(directory).rglob('*'):
                if path.is_file():
                    data = path.read_bytes()
                    self.assertFalse(any(s.encode() in data for s in secrets))
        result = self.run_clean_text(source.encode(), '-')
        self.assertTrue(result.returncode == 0)
        for secret in secrets:
            self.assertFalse(secret.encode() in output.getvalue())
            self.assertFalse(secret.encode() in result.stdout)
            self.assertFalse(secret.encode() in result.stderr)
        result = self.run_clean_text(source.encode() + b'\xff', '-')
        self.assertTrue(result.returncode != 0)
        self.assertTrue(result.stdout == b'')
        for secret in secrets:
            self.assertFalse(secret.encode() in result.stderr)


class CleanTextIdentityTests(unittest.TestCase):
    """Only synthetic identities; assertions never echo raw input."""

    run_clean_text = CleanTextTests.run_clean_text

    def check_output(self, content, expected, *args):
        result = self.run_clean_text(content.encode(), '-', *args)
        self.assertTrue(result.returncode == 0)
        self.assertTrue(result.stderr == b'')
        self.assertTrue(result.stdout == expected.encode())

    def test_repeated_email(self):
        self.check_output(
            'synthetic.person@example.test\nsynthetic.person@example.test',
            'user0@obfuscateddomain0.example\n'
            'user0@obfuscateddomain0.example')

    def test_multiple_emails(self):
        self.check_output(
            '<synthetic.one@example.test>, synthetic.two@example.test; '
            'synthetic+tag@elsewhere.invalid\r\n',
            '<user0@obfuscateddomain0.example>, '
            'user1@obfuscateddomain0.example; '
            'user2@obfuscateddomain1.example\r\n')

    def test_email_case_variants(self):
        self.check_output(
            'Synthetic.One@EXAMPLE.TEST synthetic.one@example.test',
            'user0@obfuscateddomain0.example user0@obfuscateddomain0.example')

    def test_email_assignment_context(self):
        self.check_output(
            'email=synthetic.person@example.test '
            'mailto:synthetic.person@example.test',
            'email=user0@obfuscateddomain0.example '
            'mailto:user0@obfuscateddomain0.example')

    def test_username_replacement_collision(self):
        self.check_output('obfuscateduser0 syntheticuser',
                          'obfuscateduser1 obfuscateduser2',
                          '--usernames', 'obfuscateduser0,syntheticuser')

    def test_seeded_and_unknown_username(self):
        self.check_output('syntheticuser unknownuser syntheticuser\n',
                          'obfuscateduser0 unknownuser obfuscateduser0\n',
                          '--usernames', 'syntheticuser')

    def test_repeated_comma_separated_option(self):
        self.check_output('syntheticone synthetictwo syntheticthree',
                          'obfuscateduser1 obfuscateduser2 obfuscateduser0',
                          '--usernames', 'syntheticone,synthetictwo',
                          '--usernames', 'syntheticthree')

    def test_username_case_and_short_seed(self):
        self.check_output('xy XY SyntheticUser syntheticuser',
                          'obfuscateduser0 XY obfuscateduser1 syntheticuser',
                          '--usernames', 'xy,SyntheticUser')

    def test_evidence_and_username_boundaries(self):
        content = ('user-2000048158.slice session-c33.scope\n'
                   'system_u:system_r:sshd_net_t:s0 /etc/passwd shadow-utils\n'
                   'syntheticuser-extra syntheticuser.name '
                   'syntheticuser_suffix prefixedsyntheticuser\n')
        self.check_output(content, content, '--usernames',
                          'user,session,system,sshd,shadow,syntheticuser')

    def test_exact_seed_in_evidence(self):
        self.check_output(
            'user-2000048158.slice system_u:system_r:sshd_net_t:s0',
            'obfuscateduser0 system_u:system_r:obfuscateduser1:s0',
            '--usernames', 'user-2000048158.slice,sshd_net_t')

    def test_secret_precedes_identity_parsers(self):
        self.check_output(
            'password="syntheticuser synthetic.person@example.test"\n'
            'token=synthetic.person@example.test\n'
            'synthetic.person@example.test syntheticuser',
            'password="[REDACTED_SECRET]"\ntoken=[REDACTED_TOKEN]\n'
            'user0@obfuscateddomain0.example obfuscateduser0',
            '--usernames', 'syntheticuser')

    def test_email_does_not_seed_username_or_hostname(self):
        self.check_output(
            'syntheticuser@example.test syntheticuser example.test',
            'user0@obfuscateddomain0.example syntheticuser example.test')

    def test_parser_failure_diagnostics(self):
        from sos.cleaner.text_identity import (TextEmailParser,
                                               TextUsernameParser)

        email = 'synthetic.person@example.test'
        username = 'syntheticuser'
        for parser_class in (TextEmailParser, TextUsernameParser):
            with self.subTest(parser=parser_class.name):
                with tempfile.TemporaryDirectory() as directory:
                    opts = SimpleNamespace(domains=[], hostnames=[],
                                           usernames=[username], target='-',
                                           tmp_dir=directory)
                    output, stderr = io.BytesIO(), io.StringIO()
                    with mock.patch('sos.cleaner.text.sys.stdin',
                                    buffer=io.BytesIO(email.encode())), \
                            mock.patch('sos.cleaner.text.sys.stdout',
                                       buffer=output), \
                            mock.patch('sos.cleaner.text.sys.stderr',
                                       stderr), \
                            mock.patch.object(parser_class, 'parse_line',
                                              side_effect=RuntimeError(
                                                  email + ' ' + username)):
                        with self.assertRaises(SystemExit):
                            SoSCleanText(None, opts, None).execute()
                    self.assertTrue(output.getvalue() == b'')
                    self.assertTrue('failed on line 1' in stderr.getvalue())
                    for raw in (email, 'synthetic.person', 'example.test',
                                username):
                        self.assertFalse(raw in stderr.getvalue())
                    self.assertTrue(os.listdir(directory) == [])

    def test_no_identity_cache_or_stderr_leakage(self):
        from sos.cleaner.text_identity import TextUsernameParser

        email = 'synthetic.person@example.test'
        username = 'syntheticuser'
        raw_values = (email, 'synthetic.person', 'example.test', username)
        for failure in (False, True):
            with self.subTest(failure=failure):
                with tempfile.TemporaryDirectory() as directory:
                    opts = SimpleNamespace(domains=[], hostnames=[],
                                           usernames=[username], target='-',
                                           tmp_dir=directory)
                    output, stderr = io.BytesIO(), io.StringIO()
                    source = (email + ' ' + username + '\n').encode()
                    if failure:
                        source += b'\xff'
                    parse_line = TextUsernameParser.parse_line
                    inspected = []

                    def inspect_cache(parser, line):
                        result = parse_line(parser, line)
                        for path in Path(directory).rglob('*'):
                            if path.is_dir():
                                # Cache directories sit beneath mode-0700
                                # staging; no other user can traverse it.
                                continue
                            self.assertTrue(stat.S_IMODE(path.stat().st_mode)
                                            == 0o600)
                            data = path.read_bytes()
                            for raw in raw_values:
                                self.assertFalse(raw.encode() in data)
                        inspected.append(True)
                        return result

                    with mock.patch('sos.cleaner.text.sys.stdin',
                                    buffer=io.BytesIO(source)), \
                            mock.patch('sos.cleaner.text.sys.stdout',
                                       buffer=output), \
                            mock.patch('sos.cleaner.text.sys.stderr',
                                       stderr), \
                            mock.patch.object(TextUsernameParser,
                                              'parse_line', inspect_cache), \
                            mock.patch('sos.cleaner.SoSCleaner.load_map_file',
                                       side_effect=AssertionError()), \
                            mock.patch('sos.cleaner.SoSCleaner.'
                                       'write_map_for_config',
                                       side_effect=AssertionError()):
                        if failure:
                            with self.assertRaises(SystemExit):
                                SoSCleanText(None, opts, None).execute()
                        else:
                            SoSCleanText(None, opts, None).execute()
                    self.assertTrue(bool(inspected))
                    for raw in raw_values:
                        self.assertFalse(raw in stderr.getvalue())
                        self.assertFalse(raw.encode() in output.getvalue())
                    if failure:
                        self.assertTrue(output.getvalue() == b'')
                    self.assertTrue(os.listdir(directory) == [])
