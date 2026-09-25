import os
import socket
import stat
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.report_residual import (
    ResidualMatcher, ReportTreeResidualError, ReportTreeResidualValidator,
    build_manifest_patterns, known_original_residual)
from sos.cleaner.session import SanitizationSession
from sos.cleaner.text_residual import (_has_residual, _ipv6_preserved,
                                       _packed)
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

    def test_corosync_authkey_is_rejected_regardless_of_content(self):
        for content in (b'K' * 256, b'placeholder', b''):
            with self.subTest(content_length=len(content)):
                path = self.source / 'etc/corosync/authkey'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                with self.assertRaises(ReportTreeResidualError):
                    ReportTreeResidualValidator(
                        self.source, self.manifest).validate()
                import shutil
                shutil.rmtree(self.source / 'etc')

    def test_selinux_file_contexts_bin_is_rejected_regardless_of_content(self):
        paths = ('etc/selinux/targeted/contexts/files/file_contexts.bin',
                 'etc/selinux/targeted/contexts/files/file_contexts.homedirs.bin')
        for relative in paths:
            for content in (b'X' * 580886, b'placeholder', b''):
                with self.subTest(path=relative, content_length=len(content)):
                    path = self.source / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
                    with self.assertRaises(ReportTreeResidualError):
                        ReportTreeResidualValidator(
                            self.source, self.manifest).validate()
                    import shutil
                    shutil.rmtree(self.source / 'etc')

    def test_selinux_binary_policy_is_rejected_regardless_of_content(self):
        for relative in ('etc/selinux/targeted/policy/policy.15',
                         'etc/selinux/targeted/policy/policy.31',
                         'etc/selinux/targeted/policy/policy.35'):
            with self.subTest(path=relative):
                path = self.source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'placeholder')
                with self.assertRaises(ReportTreeResidualError):
                    ReportTreeResidualValidator(
                        self.source, self.manifest).validate()
                import shutil
                shutil.rmtree(self.source / 'etc')

    def test_process_environment_is_rejected_regardless_of_content(self):
        for relative in ('proc/1/environ', 'proc/4194303/environ'):
            for content in (b'', b'LANG=C\0TOKEN=secret\0', b'placeholder'):
                with self.subTest(path=relative, length=len(content)):
                    path = self.source / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
                    with self.assertRaises(ReportTreeResidualError):
                        ReportTreeResidualValidator(
                            self.source, self.manifest).validate()
                    import shutil
                    shutil.rmtree(self.source / 'proc')

    def test_standard_ipv4_mapped_prefix_is_preserved(self):
        """A standard address-selection prefix is technical configuration."""
        for index, value in enumerate((
                '::ffff:0:0/96',
                '0:0:0:0:0:ffff:0:0/96',
                '::ffff:0.0.0.0/96',
                '::ffff:169.254.0.0/112',
                '0:0:0:0:0:ffff:a9fe:0/112',
                '::ffff:127.0.0.0/104',
                '0:0:0:0:0:ffff:7f00:0/104')):
            self.write(f'etc/gai-{index}.conf', f'#label {value} 4\n')
        result = ReportTreeResidualValidator(
            self.source, self.manifest).validate()
        self.assertEqual(result['residual_failures'], 0)

    def test_mapped_policy_prefixes_do_not_create_ipv6_mappings(self):
        before = dict(self.session.ipv6_parser.mapping.dataset)
        for value in ('::ffff:0:0/96', '::ffff:169.254.0.0/112',
                      '::ffff:127.0.0.0/104'):
            self.assertEqual(self.session.sanitize_line(value + '\n'),
                             value + '\n')
        self.assertEqual(before, self.session.ipv6_parser.mapping.dataset)

    def test_ipv4_mapped_policy_prefix_near_matches_are_residual(self):
        for value in (
                '::ffff:192.0.2.1', '::ffff:c000:0201',
                '::ffff:0:1/96', '::ffff:0:0/95',
                '::ffff:0:0/97', '::ffff:169.254.0.1/112',
                '::ffff:169.254.1.0/112', '::ffff:169.254.0.0/111',
                '::ffff:169.254.0.0/113', '::ffff:127.0.0.1/104',
                '::ffff:127.1.0.0/104', '::ffff:127.0.0.0/103',
                '::ffff:127.0.0.0/105', '::ffff:0:0'):
            with self.subTest(value=value):
                self.assertTrue(_has_residual(value, set(), set()))

        address = _packed('::ffff:0:0/96', socket.AF_INET6)
        self.assertFalse(_ipv6_preserved('::ffff:0:0/96x', address))
        self.assertFalse(_ipv6_preserved('x::ffff:0:0/96', address))

    def test_standard_mapped_link_local_policy_prefix_is_preserved(self):
        """The fixed mapped link-local policy prefix is technical syntax."""
        self.write('etc/gai.conf',
                   '#label ::ffff:169.254.0.0/112 4\n')
        result = ReportTreeResidualValidator(
            self.source, self.manifest).validate()
        self.assertEqual(result['residual_failures'], 0)

    def test_systemd_instance_unit_is_not_email_residual(self):
        """An instance unit containing @ is not an email address."""
        self.write('proc/cgroup',
                   '/system.slice/system-postfix.slice/postfix@-.service\n')
        result = ReportTreeResidualValidator(
            self.source, self.manifest).validate()
        self.assertEqual(result['residual_failures'], 0)

    def test_mapped_contiguous_mac_form_is_not_left_as_original(self):
        """A mapped MAC in contiguous form must not survive validation."""
        self.write('proc/dev_mcast',
                   '1234567890ab\n')
        with self.assertRaises(ReportTreeResidualError):
            ReportTreeResidualValidator(self.source, self.manifest).validate()

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

    def test_compiled_residual_matcher_matches_individual_patterns(self):
        mappings = self.manifest.raw_mappings()
        individual = build_manifest_patterns(mappings)
        matcher = ResidualMatcher(mappings)
        cases = (
            ('safe technical text', False),
            ('node', True),
            ('node-extra', False),
            ('customer.example', True),
            ('10.20.30.40', True),
            ('2001:db8::10', True),
            ('12:34:56:78:90:ab', True),
            ('alice@example.test', True),
            ('alice-admin', False),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(
                    known_original_residual(text, individual), expected)
                self.assertEqual(matcher.search(text), expected)

    def test_compiled_residual_matcher_handles_overlapping_originals(self):
        mappings = {namespace: {} for namespace in (
            'hostnames', 'domains', 'ipv4', 'ipv6', 'mac', 'emails',
            'usernames')}
        mappings['hostnames'] = {
            'node': 'host0', 'node.example': 'host1',
            'node+special': 'host2',
        }
        individual = build_manifest_patterns(mappings)
        matcher = ResidualMatcher(mappings)
        for text in ('node', 'node.example', 'node+special', 'node-other'):
            with self.subTest(text=text):
                self.assertEqual(
                    matcher.search(text),
                    known_original_residual(text, individual))

    def test_residual_matcher_prefilter_is_conservative(self):
        mappings = self.manifest.raw_mappings()
        individual = build_manifest_patterns(mappings)
        matcher = ResidualMatcher(mappings)
        for namespace, values in mappings.items():
            if namespace == 'schema_version':
                continue
            for original, _alias in values.items():
                with self.subTest(namespace=namespace, original=original):
                    self.assertTrue(matcher.may_match(original))
                    self.assertEqual(
                        matcher.search(original),
                        known_original_residual(original, individual))
        self.assertFalse(matcher.may_match('zzzz'))

    def test_residual_matcher_skips_impossible_lines(self):
        matcher = ResidualMatcher(self.manifest.raw_mappings())
        self.assertFalse(matcher.search('zzzz'))
        self.assertTrue(matcher.search('node'))

    def test_residual_failure_exposes_only_safe_category_and_path(self):
        self.write('safe/path.txt', 'node\n')
        with self.assertRaises(ReportTreeResidualError) as context:
            ReportTreeResidualValidator(
                self.source, self.manifest).validate()
        error = context.exception
        self.assertEqual(error.category, 'known hostname')
        self.assertEqual(error.relative_path, ('safe', 'path.txt'))
        self.assertNotIn('node', str(error))

    def test_optimized_matcher_matches_reference_on_edge_cases(self):
        mappings = {namespace: {} for namespace in (
            'hostnames', 'domains', 'ipv4', 'ipv6', 'mac', 'emails',
            'usernames')}
        mappings['hostnames'] = {
            'Node': 'host0', 'node.example': 'host1',
            'node+special': 'host2'}
        mappings['mac'] = {'aa:bb:cc:dd:ee:ff': 'mac0'}
        mappings['emails'] = {'Alice@Example.test': 'mail0'}
        matcher = ResidualMatcher(mappings)
        reference = build_manifest_patterns(mappings)
        cases = (
            '', 'safe text', 'Node', 'node-extra', 'NODE',
            'node.example', 'node+special', 'aa:bb:cc:dd:ee:ff',
            'aabbccddeeff', 'aa-bb-cc-dd-ee-ff',
            'Alice@Example.test', 'ALICE@EXAMPLE.TEST',
            'xnode', 'node_', 'prefix node suffix', 'naïve text')
        for text in cases:
            with self.subTest(text=text):
                expected = known_original_residual(text, reference)
                self.assertEqual(matcher.search(text), expected)

    def test_optimized_matcher_preserves_case_sensitive_usernames(self):
        mappings = {namespace: {} for namespace in (
            'hostnames', 'domains', 'ipv4', 'ipv6', 'mac', 'emails',
            'usernames')}
        mappings['usernames'] = {'Alice': 'obfuscateduser0'}
        matcher = ResidualMatcher(mappings)
        reference = build_manifest_patterns(mappings)
        for text in ('Alice', 'alice', 'ALICE', 'prefix Alice suffix',
                     'prefix alice suffix'):
            with self.subTest(text=text):
                self.assertEqual(matcher.search(text),
                                 known_original_residual(text, reference))


if __name__ == '__main__':
    unittest.main()
