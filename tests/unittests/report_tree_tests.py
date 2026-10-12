import os
import stat
import struct
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from sos.cleaner.discovery import ReportIdentityDiscovery
from sos.cleaner.openpgp import is_public_keyring_fd
from sos.cleaner.tzif import is_tzif_fd
from sos.cleaner.session import SanitizationSession
from sos.cleaner.tree import ReportTreeSanitizer, ReportTreeSanitizerError
from sos.cleaner.report_residual import ReportTreeResidualError


class ReportTreeTests(unittest.TestCase):
    def setUp(self):
        self.source_dir = tempfile.TemporaryDirectory()
        self.session_dir = tempfile.TemporaryDirectory()
        self.output_parent = tempfile.TemporaryDirectory()
        self.authkey_sessions = []
        self.authkey_case_id = 0
        self.source = Path(self.source_dir.name)
        self.session = SanitizationSession(
            self.session_dir.name,
            hostnames=('seedhost',), domains=('sensitive.example',),
            usernames=('alice',))

    def tearDown(self):
        self.output_parent.cleanup()
        self.session_dir.cleanup()
        self.source_dir.cleanup()
        for session in self.authkey_sessions:
            session.cleanup()

    def write(self, relative, content, binary=False):
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if binary:
            path.write_bytes(content)
        else:
            path.write_text(content, encoding='utf-8')

    def discover(self):
        self.write('hostname', 'node\n')
        self.write('sos_commands/networking/ip_-o_addr',
                   '2: eth0 inet 10.20.30.40/24 scope global\n')
        self.write('var/log/auth.log', 'acct="alice"\n')
        return ReportIdentityDiscovery(self.source, self.session).discover()

    def destination(self, name='output'):
        return Path(self.output_parent.name) / name

    def _run_authkey_case(self, relative='etc/corosync/authkey', size=256,
                          setup=None, content=None):
        for child in self.source.iterdir():
            if child.is_dir():
                import shutil
                shutil.rmtree(child)
            else:
                child.unlink()
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'K' * size if content is None else content)
        if setup is not None:
            setup(path)
        session_dir = tempfile.TemporaryDirectory()
        self.authkey_sessions.append(session_dir)
        session = SanitizationSession(session_dir.name)
        self.authkey_case_id += 1
        destination = self.destination(f'authkey-output-{self.authkey_case_id}')
        return ReportTreeSanitizer(self.source, destination, session), \
            destination

    def test_corosync_authkey_exact_supported_sizes_is_omitted(self):
        for size in (128, 256, 4096):
            with self.subTest(size=size):
                sanitizer, destination = self._run_authkey_case(size=size)
                result = sanitizer.sanitize()
                self.assertFalse((destination / 'etc/corosync/authkey').exists())
                self.assertEqual(result['cluster_authkeys_omitted'], 1)
                self.assertEqual(result['binary_files_omitted'], 1)

    def test_tree_error_preserves_safe_residual_cause(self):
        self.write('details.txt', 'safe\n')
        destination = self.destination('residual-cause')
        cause = ReportTreeResidualError(
            {}, 'known hostname', ('details.txt',))
        with mock.patch('sos.cleaner.tree.ReportTreeResidualValidator.validate',
                        side_effect=cause):
            with self.assertRaises(ReportTreeSanitizerError) as context:
                ReportTreeSanitizer(
                    self.source, destination, self.session).sanitize()
        self.assertIs(context.exception.__cause__, cause)
        self.assertEqual(context.exception.__cause__.category,
                         'known hostname')
        self.assertEqual(context.exception.__cause__.relative_path,
                         ('details.txt',))
        self.assertNotIn('safe', str(context.exception))

    def test_corosync_authkey_invalid_size_fails_closed(self):
        for size in (0, 1, 127, 4097):
            with self.subTest(size=size):
                sanitizer, destination = self._run_authkey_case(size=size)
                with self.assertRaises(ReportTreeSanitizerError):
                    sanitizer.sanitize()
                self.assertFalse(destination.exists())

    def test_corosync_authkey_exact_path_and_object_policy(self):
        cases = (
            ('etc/other/authkey', None),
            ('other/authkey', None),
            ('etc/pacemaker/authkey', None),
            ('etc/corosync/custom.key', None),
        )
        for relative, _ in cases:
            with self.subTest(relative=relative):
                sanitizer, _destination = self._run_authkey_case(
                    relative, content=b'\x00' + (b'K' * 255))
                with self.assertRaises(ReportTreeSanitizerError):
                    sanitizer.sanitize()

    def test_wrong_path_utf8_authkey_like_content_uses_text_policy(self):
        sanitizer, destination = self._run_authkey_case('etc/other/authkey')
        result = sanitizer.sanitize()
        self.assertEqual(result['unsupported_files'], 0)
        self.assertTrue((destination / 'etc/other/authkey').exists())
        self.assertEqual(result['cluster_authkeys_omitted'], 0)

        def make_symlink(path):
            path.unlink()
            path.symlink_to('target')

        sanitizer, _destination = self._run_authkey_case(setup=make_symlink)
        with self.assertRaises(ReportTreeSanitizerError):
            sanitizer.sanitize()

        def make_hardlink(path):
            sibling = path.with_name('other-key')
            sibling.write_bytes(path.read_bytes())
            path.unlink()
            os.link(sibling, path)

        sanitizer, _destination = self._run_authkey_case(setup=make_hardlink)
        with self.assertRaises(ReportTreeSanitizerError):
            sanitizer.sanitize()

    def test_corosync_authkey_is_not_read_during_mapping_stabilization(self):
        sanitizer, _destination = self._run_authkey_case()
        original = sanitizer._is_text_fd
        calls = []

        def observe(fd):
            calls.append(os.fstat(fd).st_size)
            return original(fd)

        sanitizer._is_text_fd = observe
        result = sanitizer.sanitize()
        self.assertNotIn(256, calls)
        self.assertEqual(result['cluster_authkeys_omitted'], 1)

    def test_copy_stat_uses_verified_descriptor_metadata_operations(self):
        path = self.source / 'metadata.txt'
        path.write_text('metadata\n', encoding='utf-8')
        fd = os.open(path, os.O_RDWR)
        try:
            source_stat = os.fstat(fd)
            with mock.patch.object(
                    os, 'chmod', side_effect=AssertionError('path chmod')):
                ReportTreeSanitizer._copy_stat(
                    source_stat, destination_fd=fd)
        finally:
            os.close(fd)

    def test_copy_stat_fails_closed_without_fd_metadata_support(self):
        path = self.source / 'metadata.txt'
        path.write_text('metadata\n', encoding='utf-8')
        fd = os.open(path, os.O_RDWR)
        try:
            source_stat = os.fstat(fd)
            with mock.patch.object(os, 'fchmod', None):
                with self.assertRaises(OSError):
                    ReportTreeSanitizer._copy_stat(
                        source_stat, destination_fd=fd)
        finally:
            os.close(fd)

    def test_copy_stat_uses_descriptor_for_directory_metadata(self):
        path = self.source / 'metadata-dir'
        path.mkdir()
        flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | \
            getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(path, flags)
        try:
            source_stat = os.fstat(fd)
            with mock.patch.object(
                    os, 'chmod', side_effect=AssertionError('path chmod')):
                ReportTreeSanitizer._copy_stat(
                    source_stat, destination_fd=fd)
        finally:
            os.close(fd)

    def test_selinux_file_contexts_bin_size_and_path_policy(self):
        targets = sorted(ReportTreeSanitizer._selinux_file_contexts_bin_paths)
        accepted = (1, 7, 8, 580886, 8 * 1024 * 1024)
        rejected = (0, 8 * 1024 * 1024 + 1)
        for target in targets:
            for size in accepted:
                path = self.source.joinpath(*target)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'X' * size)
                observed = path.stat()
                self.assertEqual(
                    ReportTreeSanitizer._selinux_file_contexts_bin_policy(
                        target, observed), 'omit')
                path.unlink()
            for size in rejected:
                path = self.source.joinpath(*target)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'X' * size)
                observed = path.stat()
                self.assertEqual(
                    ReportTreeSanitizer._selinux_file_contexts_bin_policy(
                        target, observed), 'reject')
                path.unlink()
        for relative in (
                ('etc', 'selinux', 'other', 'contexts', 'files',
                 'file_contexts.bin'),
                ('etc', 'selinux', 'targeted', 'contexts', 'files',
                 'file_contexts.local.bin'),
                ('other', 'file_contexts.bin')):
            self.assertIsNone(
                ReportTreeSanitizer._selinux_file_contexts_bin_policy(
                    relative, observed))

    def test_selinux_file_contexts_bin_rejects_non_regular_or_hardlinked(self):
        target = ('etc', 'selinux', 'targeted', 'contexts', 'files',
                  'file_contexts.bin')
        path = self.source.joinpath(*target)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'X' * 580886)
        sibling = path.with_name('other.bin')
        os.link(path, sibling)
        self.assertEqual(
            ReportTreeSanitizer._selinux_file_contexts_bin_policy(
                target,
                path.stat()), 'reject')
        path.unlink()
        sibling.unlink()
        path.symlink_to('other.bin')
        self.assertEqual(
            ReportTreeSanitizer._selinux_file_contexts_bin_policy(
                target,
                path.lstat()), 'reject')
        path.unlink()
        os.mkfifo(path)
        self.assertEqual(
            ReportTreeSanitizer._selinux_file_contexts_bin_policy(
                target,
                path.lstat()), 'reject')

    def test_selinux_binary_policy_header_and_filename_policy(self):
        target = self.source / 'etc/selinux/targeted/policy'
        target.mkdir(parents=True)

        def header(version=31, magic=0xf97cff8c, identifier=b'SE Linux',
                   symbol_count=8, ocon_count=9):
            return (struct.pack('<2I', magic, len(identifier)) + identifier +
                    struct.pack('<4I', version, 0, symbol_count,
                                ocon_count))

        for version in (15, 31, 35):
            path = target / f'policy.{version}'
            path.write_bytes(header(version))
            fd = os.open(path, os.O_RDONLY)
            try:
                self.assertEqual(
                    ReportTreeSanitizer._selinux_binary_policy(
                        tuple(path.relative_to(self.source).parts),
                        path.stat(), fd), 'omit')
            finally:
                os.close(fd)
            path.unlink()

        cases = (
            ('policy.14', header(14)),
            ('policy.36', header(36)),
            ('policy.031', header(31)),
            ('policy.+31', header(31)),
            ('policy.-31', header(31)),
            ('policy.31x', header(31)),
            ('policy.31', header(30)),
            ('policy.31', header(magic=0)),
            ('policy.31', header(identifier=b'XenFlask')),
            ('policy.31', header(ocon_count=0)),
            ('policy.31', header()[:-1]),
        )
        for name, content in cases:
            with self.subTest(name=name, length=len(content)):
                path = target / name
                path.write_bytes(content)
                fd = os.open(path, os.O_RDONLY)
                try:
                    relative = tuple(path.relative_to(self.source).parts)
                    self.assertEqual(
                        ReportTreeSanitizer._selinux_binary_policy(
                            relative, path.stat(), fd), 'reject')
                finally:
                    os.close(fd)
                path.unlink()

        path = target / 'policy.31'
        path.write_bytes(header(31))
        with path.open('r+b') as stream:
            stream.truncate(64 * 1024 * 1024)
        fd = os.open(path, os.O_RDONLY)
        try:
            self.assertEqual(
                ReportTreeSanitizer._selinux_binary_policy(
                    tuple(path.relative_to(self.source).parts), path.stat(), fd),
                'omit')
        finally:
            os.close(fd)

    def test_selinux_binary_policy_is_not_generic_or_other_policy_type(self):
        cases = (
            ('etc/selinux/targeted/policy/policy.kern',),
            ('etc/selinux/mls/policy/policy.31',),
            ('etc/selinux/targeted/policy/nested/policy.31',),
            ('etc/selinux/targeted/policy/file_contexts.bin',),
            ('etc/other/policy/policy.31',),
        )
        for relative in cases:
            self.assertIsNone(
                ReportTreeSanitizer._selinux_binary_policy(relative, -1, -1))

    @staticmethod
    def openpgp_packet(tag, body=b'\x04\x00synthetic-public-key'):
        """Build a small old-format packet fixture without real key data."""
        return bytes((0x80 | (tag << 2), len(body))) + body

    @staticmethod
    def tzif(version=b'2', counts=(0, 0, 0, 0, 1, 4),
             footer=b'\nUTC0\n'):
        import struct
        header = b'TZif' + version + (b'\0' * 15) + struct.pack('>6I', *counts)
        block = b'\0\0\0\0\0\0' + b'UTC\0'
        return header + block + header + block + footer

    def test_tree_is_copied_and_sanitized_with_shared_session(self):
        self.discover()
        self.write('logs/node/status.log',
                   'node 10.20.30.40 alice@example.test\n')
        self.write('systemd/user-2000048158.slice',
                   'system_u:system_r:sshd_net_t:s0\n')
        self.write('technical/ip_-o_addr', '10.20.30.40\n')
        self.write('aliases.txt',
                   'host0 user0@obfuscateddomain0.example obfuscateduser0\n')
        source_snapshot = {
            path.relative_to(self.source): path.read_bytes()
            for path in self.source.rglob('*') if path.is_file()
        }

        result = ReportTreeSanitizer(
            self.source, self.destination(), self.session).sanitize()

        self.assertGreaterEqual(result['files_processed'], 5)
        self.assertGreaterEqual(result['paths_renamed'], 1)
        output = self.destination()
        node_alias = self.session.hostname_parser.mapping.hosts['node']
        ip_alias = self.session.ip_parser.mapping.dataset['10.20.30.40/24']
        ip_alias = ip_alias.split('/', 1)[0]
        sanitized = (output / 'logs' / node_alias / 'status.log').read_text()
        self.assertIn(node_alias, sanitized)
        self.assertIn(ip_alias, sanitized)
        self.assertIn('user0@obfuscateddomain0.example', sanitized)
        self.assertEqual((output / 'systemd' / 'user-2000048158.slice').read_text(),
                         'system_u:system_r:sshd_net_t:s0\n')
        self.assertTrue((output / 'technical' / 'ip_-o_addr').exists())
        self.assertEqual((output / 'aliases.txt').read_text(),
                         'host0 user0@obfuscateddomain0.example '
                         'obfuscateduser0\n')
        for relative, content in source_snapshot.items():
            self.assertEqual((self.source / relative).read_bytes(), content)

    def test_netstat_leading_compressed_ipv6_is_sanitized(self):
        """Netstat's leading-compressed local address uses the IPv6 parser."""
        synthetic = '::1234:abcd'
        alias = self.session.add_ipv6(synthetic)
        self.write(
            'sos_commands/networking/netstat_-W_-neopa',
            'tcp6 0 0 ' + synthetic + ' :::* LISTEN 1234/synthetic\n')

        result = ReportTreeSanitizer(
            self.source, self.destination('netstat-ipv6'), self.session
        ).sanitize()

        output = (self.destination('netstat-ipv6') /
                  'sos_commands/networking/netstat_-W_-neopa').read_text()
        self.assertNotEqual(alias, synthetic)
        self.assertNotIn(synthetic, output)
        self.assertEqual(result['text_files_sanitized'], 1)

    def test_late_contextual_username_applies_to_earlier_file(self):
        """Contextual discovery must not make output traversal-dependent."""
        self.write('a-plain.txt', 'lateuser diagnostic evidence\n')
        self.write('z-context.txt', 'user=lateuser\n')

        result = ReportTreeSanitizer(
            self.source, self.destination(), self.session).sanitize()

        alias = self.session.username_parser.mapping.dataset['lateuser']
        self.assertEqual(result['text_files_sanitized'], 2)
        self.assertEqual(
            (self.destination() / 'a-plain.txt').read_text(encoding='utf-8'),
            f'{alias} diagnostic evidence\n')
        self.assertEqual(
            (self.destination() / 'z-context.txt').read_text(encoding='utf-8'),
            f'user={alias}\n')

    def test_late_contextual_username_sanitizes_an_earlier_path(self):
        self.write('lateuser/log.txt', 'diagnostic evidence\n')
        self.write('z-context.txt', 'user=lateuser\n')

        ReportTreeSanitizer(
            self.source, self.destination(), self.session).sanitize()

        alias = self.session.username_parser.mapping.dataset['lateuser']
        self.assertTrue((self.destination() / alias / 'log.txt').exists())
        self.assertFalse((self.destination() / 'lateuser').exists())

    def test_collision_fails_closed(self):
        self.session.add_hostname('node')
        self.write('node', 'one\n')
        self.write('host1', 'two\n')
        destination = self.destination()
        with self.assertRaises(ReportTreeSanitizerError):
            ReportTreeSanitizer(self.source, destination,
                                self.session).sanitize()
        self.assertFalse(destination.exists())

    def test_existing_destination_is_not_overwritten(self):
        destination = self.destination()
        destination.mkdir()
        marker = destination / 'marker'
        marker.write_text('keep', encoding='utf-8')
        with self.assertRaises(ReportTreeSanitizerError):
            ReportTreeSanitizer(self.source, destination,
                                self.session).sanitize()
        self.assertEqual(marker.read_text(), 'keep')

    def test_destination_created_before_publication_fails_closed(self):
        destination = self.destination()

        class RaceSanitizer(ReportTreeSanitizer):
            def _publish_noreplace(inner_self, staging):
                destination.mkdir()
                (destination / 'marker').write_text('keep', encoding='utf-8')
                super()._publish_noreplace(staging)

        with self.assertRaises(ReportTreeSanitizerError):
            RaceSanitizer(self.source, destination,
                          self.session).sanitize()
        self.assertTrue(destination.is_dir())
        self.assertEqual((destination / 'marker').read_text(), 'keep')

    def test_malformed_and_binary_files_are_not_published(self):
        self.write('good.txt', 'node\n')
        self.write('bad.bin', b'valid-prefix\xff\x00', binary=True)
        destination = self.destination()
        with self.assertRaises(ReportTreeSanitizerError) as context:
            ReportTreeSanitizer(self.source, destination,
                                self.session).sanitize()
        self.assertEqual(context.exception.summary['unsupported_files'], 1)
        self.assertFalse(destination.exists())

    def test_approved_binary_classes_are_omitted_and_counted(self):
        sysstat = b'\x96\xd5\x75\x21\x00sysstat-binary'
        proc_pci = b'\x00\xffpci-config-space'
        apt_xz = b'\xfd7zXZ\x00opaque-compressed-log'
        self.write('var/log/sysstat/sa01', sysstat, binary=True)
        self.write('proc/bus/pci/00/00.0', proc_pci, binary=True)
        self.write('var/log/apt/eipp.log.xz', apt_xz, binary=True)
        self.write('details/something.gz', 'seedhost diagnostic text\n')
        source_snapshot = {
            path.relative_to(self.source): path.read_bytes()
            for path in self.source.rglob('*') if path.is_file()
        }

        result = ReportTreeSanitizer(
            self.source, self.destination(), self.session).sanitize()

        self.assertEqual(result['binary_files_omitted'], 3)
        self.assertEqual(result['sysstat_files_omitted'], 1)
        self.assertEqual(result['proc_sys_files_omitted'], 1)
        self.assertEqual(result['compressed_files_omitted'], 1)
        output = self.destination()
        self.assertFalse((output / 'var/log/sysstat/sa01').exists())
        self.assertFalse((output / 'proc/bus/pci/00/00.0').exists())
        self.assertFalse((output / 'var/log/apt/eipp.log.xz').exists())
        self.assertEqual((output / 'details/something.gz').read_text(),
                         'host0 diagnostic text\n')
        for relative, content in source_snapshot.items():
            self.assertEqual((self.source / relative).read_bytes(), content)

    def test_binary_omission_requires_exact_path_and_signature(self):
        cases = {
            'details/sa01': b'\x96\xd5\x75\x21\x00binary',
            'var/log/sysstat/not-sa': b'\x96\xd5\x75\x21\x00binary',
            'var/log/sysstat/sa01': b'wrong-magic\x00binary',
            'proc/bus/pci/not-a-device': b'\x00binary',
            'var/log/apt/other.xz': b'\xfd7zXZ\x00binary',
            'var/log/apt/eipp.log.xz': b'wrong-magic\x00binary',
        }
        for index, (relative, content) in enumerate(cases.items()):
            with self.subTest(relative=relative):
                path = self.source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                destination = self.destination(f'exact-{index}')
                with self.assertRaises(ReportTreeSanitizerError):
                    ReportTreeSanitizer(
                        self.source, destination, self.session).sanitize()
                self.assertFalse(destination.exists())
                path.unlink()

    def test_process_environment_policy_is_narrow(self):
        valid = ('proc/1/environ', 'proc/123/environ',
                 'proc/4194303/environ')
        for index, relative in enumerate(valid):
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'LANG=C\0TOKEN=secret\0')
            sanitizer = ReportTreeSanitizer(
                self.source, self.destination(f'environ-{index}'), self.session)
            self.assertEqual(
                sanitizer._process_environment_policy(
                    tuple(path.relative_to(self.source).parts), path.stat()),
                'omit')
            path.unlink()

        negatives = (
            'proc/0/environ', 'proc/4194304/environ', 'proc/01/environ',
            'proc/+1/environ', 'proc/-1/environ', 'proc/ 1/environ',
            'proc/١/environ', 'proc/self/environ',
            'proc/thread-self/environ', 'proc/1/environment',
            'proc/1/foo/environ', 'proc/foo/environ',
            'proc/nested/1/environ',
        )
        observed = type('Observed', (), {
            'st_mode': stat.S_IFREG | 0o600, 'st_nlink': 1, 'st_size': 20})()
        for relative in negatives:
            self.assertIsNone(
                ReportTreeSanitizer._process_environment_policy(
                    tuple(relative.split('/')), observed))

    def test_process_environment_size_and_object_policy(self):
        relative = ('proc', '1', 'environ')
        path = self.source.joinpath(*relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        for size in (0, 1, 8 * 1024 * 1024):
            with self.subTest(size=size):
                with path.open('wb') as stream:
                    stream.truncate(size)
                self.assertEqual(
                    ReportTreeSanitizer._process_environment_policy(
                        relative, path.stat()), 'omit')
        with path.open('wb') as stream:
            stream.truncate(8 * 1024 * 1024 + 1)
        self.assertEqual(
            ReportTreeSanitizer._process_environment_policy(
                relative, path.stat()), 'reject')

        for mode, nlink in ((stat.S_IFLNK, 1), (stat.S_IFREG, 2),
                            (stat.S_IFIFO, 1), (stat.S_IFDIR, 1),
                            (stat.S_IFSOCK, 1), (stat.S_IFCHR, 1)):
            observed = type('Observed', (), {
                'st_mode': mode | 0o600, 'st_nlink': nlink,
                'st_size': 20})()
            self.assertEqual(
                ReportTreeSanitizer._process_environment_policy(
                    relative, observed), 'reject')

    def test_process_environment_is_omitted_before_content_processing(self):
        path = self.source / 'proc/1/environ'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'PASSWORD=secret\0')
        destination = self.destination('environ-boundary')
        sanitizer = ReportTreeSanitizer(self.source, destination, self.session)
        sanitizer._is_text_fd = lambda fd: self.fail('text probe called')
        sanitizer._binary_omission_class = lambda relative, fd: self.fail(
            'binary probe called')
        parent_fd = os.open(path.parent, os.O_RDONLY)
        try:
            sanitizer._copy_file(
                'environ', parent_fd, path.stat(),
                destination / 'proc/1/environ', ('proc', '1', 'environ'))
        finally:
            os.close(parent_fd)
        self.assertEqual(sanitizer._summary['process_environments_omitted'], 1)
        self.assertEqual(sanitizer._summary['binary_files_omitted'], 1)
        self.assertEqual(sanitizer._summary['proc_sys_files_omitted'], 0)
        self.assertFalse((destination / 'proc/1/environ').exists())

    def test_high_risk_and_non_utf8_binary_classes_fail_closed(self):
        cases = {
            'unknown.bin': b'\x00\x01opaque',
            'non-utf8.log': b'diagnostic\xfftext',
            'database.sqlite': b'SQLite format 3\x00data',
            'executable': b'\x7fELF\x02\x01\x00data',
            'image.png': b'\x89PNG\r\n\x1a\n\x00data',
            'certificate.der': b'0\x82\x00\x01certificate',
            'private-key.p12': b'0\x82\x00\x01private-key',
            'misleading.txt': b'plain-name\x00binary',
        }
        for index, (relative, content) in enumerate(cases.items()):
            with self.subTest(relative=relative):
                path = self.source / relative
                path.write_bytes(content)
                destination = self.destination(f'high-risk-{index}')
                with self.assertRaises(ReportTreeSanitizerError):
                    ReportTreeSanitizer(
                        self.source, destination, self.session).sanitize()
                self.assertFalse(destination.exists())
                path.unlink()

    def test_public_only_apt_keyrings_are_omitted(self):
        keyring = self.openpgp_packet(6)
        cases = ('etc/apt/trusted.gpg',
                 'etc/apt/trusted.gpg.d/synthetic.gpg')
        for index, relative in enumerate(cases):
            with self.subTest(relative=relative):
                path = self.source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(keyring)
                result = ReportTreeSanitizer(
                    self.source, self.destination(f'keyring-{index}'),
                    self.session).sanitize()
                self.assertEqual(result['package_keyrings_omitted'], 1)
                self.assertFalse(
                    (self.destination(f'keyring-{index}') / relative).exists())
                path.unlink()

    def test_exact_timezone_file_is_omitted_and_counted(self):
        path = self.source / 'usr/share/zoneinfo/Etc/UTC'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.tzif())
        with path.open('rb') as stream:
            self.assertTrue(is_tzif_fd(stream.fileno()))
        result = ReportTreeSanitizer(
            self.source, self.destination(), self.session).sanitize()
        self.assertEqual(result['timezone_files_omitted'], 1)
        self.assertEqual(result['binary_files_omitted'], 1)
        self.assertFalse((self.destination() / 'usr/share/zoneinfo/Etc/UTC').exists())

    def test_two_timezone_files_are_counted_once_each_across_two_passes(self):
        for relative in ('usr/share/zoneinfo/Etc/UTC',
                         'usr/share/zoneinfo/Australia/Sydney'):
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.tzif())
        result = ReportTreeSanitizer(
            self.source, self.destination(), self.session).sanitize()
        self.assertEqual(result['timezone_files_omitted'], 2)
        self.assertEqual(result['binary_files_omitted'], 2)

    def test_timezone_omission_requires_exact_path_and_valid_structure(self):
        valid = self.tzif()
        cases = {
            'usr/share/zoneinfo/Etc/GMT': valid,
            'usr/share/zoneinfo/UTC': valid,
            'etc/UTC': valid,
            'usr/share/zoneinfo/Etc/UTC-copy': valid,
            'usr/share/zoneinfo/Etc/UTC': b'TZif' + b'\0' * 20,
            'usr/share/zoneinfo/Etc/UTC.bad': valid,
        }
        for index, (relative, content) in enumerate(cases.items()):
            with self.subTest(relative=relative):
                path = self.source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                destination = self.destination(f'tzif-rejected-{index}')
                with self.assertRaises(ReportTreeSanitizerError):
                    ReportTreeSanitizer(
                        self.source, destination, self.session).sanitize()
                self.assertFalse(destination.exists())
                path.unlink()

    def test_tzif_classifier_rejects_unsupported_or_malformed_inputs(self):
        cases = (
            self.tzif(version=b'1'),
            self.tzif(counts=(0, 0, 0, 0, 1, 4), footer=b'bad'),
            self.tzif()[:-1],
            b'TZif2' + b'\0' * 39,
        )
        for content in cases:
            path = self.source / 'usr/share/zoneinfo/Etc/UTC'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            with path.open('rb') as stream:
                self.assertFalse(is_tzif_fd(stream.fileno()))
            with self.assertRaises(ReportTreeSanitizerError):
                ReportTreeSanitizer(
                    self.source, self.destination(), self.session).sanitize()
            self.assertFalse(self.destination().exists())
            path.unlink()

    def test_tzif_accepts_type_count_indicators_used_by_rhel(self):
        import struct
        counts = (4, 4, 0, 2, 4, 4)
        header = (b'TZif2' + (b'\0' * 15) +
                  struct.pack('>6I', *counts))
        block = (b'\0' * 8 + b'\0' * 2 +
                 (b'\0\0\0\0\0\0' * 4) + b'UTC\0' +
                 b'\0' * 4 + b'\0' * 4)
        block64 = (b'\0' * 16 + b'\0' * 2 +
                   (b'\0\0\0\0\0\0' * 4) + b'UTC\0' +
                   b'\0' * 4 + b'\0' * 4)
        content = header + block + header + block64 + b'\nUTC0\n'
        path = self.source / 'usr/share/zoneinfo/Etc/UTC'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        with path.open('rb') as stream:
            self.assertTrue(is_tzif_fd(stream.fileno()))
        path.unlink()

    def test_oversized_tzif_is_not_omitted(self):
        path = self.source / 'usr/share/zoneinfo/Etc/UTC'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.tzif() + b'x' * (1024 * 1024))
        with self.assertRaises(ReportTreeSanitizerError):
            ReportTreeSanitizer(
                self.source, self.destination(), self.session).sanitize()
        self.assertFalse(self.destination().exists())

    def test_public_only_keyring_supports_common_public_packets(self):
        keyring = b''.join((self.openpgp_packet(6),
                            self.openpgp_packet(13, b'synthetic-user-id'),
                            self.openpgp_packet(14)))
        path = self.source / 'etc/apt/trusted.gpg.d/synthetic.gpg'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(keyring)
        with path.open('rb') as stream:
            self.assertTrue(is_public_keyring_fd(stream.fileno()))

        result = ReportTreeSanitizer(
            self.source, self.destination(), self.session).sanitize()
        self.assertEqual(result['package_keyrings_omitted'], 1)

    def test_secret_or_malformed_apt_keyrings_fail_closed(self):
        cases = {
            'secret.gpg': self.openpgp_packet(5),
            'secret-subkey.gpg': self.openpgp_packet(7),
            'truncated.gpg': b'\x98\x20short',
            'arbitrary.gpg': b'\x00\x01\x02\x00arbitrary',
        }
        for index, (name, content) in enumerate(cases.items()):
            with self.subTest(name=name):
                path = self.source / 'etc/apt/trusted.gpg.d' / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                destination = self.destination(f'rejected-keyring-{index}')
                with self.assertRaises(ReportTreeSanitizerError):
                    ReportTreeSanitizer(
                        self.source, destination, self.session).sanitize()
                self.assertFalse(destination.exists())
                path.unlink()

    def test_approved_keyring_path_is_required_for_omission(self):
        content = self.openpgp_packet(6)
        path = self.source / 'etc/apt/other.gpg'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        with self.assertRaises(ReportTreeSanitizerError):
            ReportTreeSanitizer(
                self.source, self.destination(), self.session).sanitize()
        self.assertFalse(self.destination().exists())

    def test_separate_sessions_do_not_share_path_mappings(self):
        self.session.add_hostname('node')
        other_dir = tempfile.TemporaryDirectory()
        self.addCleanup(other_dir.cleanup)
        other = SanitizationSession(other_dir.name)
        self.write('node/file.txt', 'node\n')
        first = self.destination('first')
        ReportTreeSanitizer(self.source, first, self.session).sanitize()
        second = self.destination('second')
        ReportTreeSanitizer(self.source, second, other).sanitize()
        self.assertTrue((first / 'host1' / 'file.txt').exists())
        self.assertTrue((second / 'node' / 'file.txt').exists())

    def test_internal_symlink_is_recreated_with_rewritten_target(self):
        self.session.add_hostname('node')
        self.write('node/log', 'node\n')
        link = self.source / 'links' / 'current'
        link.parent.mkdir()
        link.symlink_to('../node/log')

        result = ReportTreeSanitizer(
            self.source, self.destination(), self.session).sanitize()

        self.assertEqual(result['symlinks_preserved'], 1)
        output_link = self.destination() / 'links' / 'current'
        self.assertTrue(output_link.is_symlink())
        self.assertEqual(os.readlink(output_link), '../host1/log')

    def test_absolute_escape_loop_and_dangling_symlinks_fail_or_preserve(self):
        absolute = self.source / 'absolute'
        absolute.symlink_to('/etc/passwd')
        with self.assertRaises(ReportTreeSanitizerError):
            ReportTreeSanitizer(self.source, self.destination('absolute-out'),
                                self.session).sanitize()
        self.assertFalse(self.destination('absolute-out').exists())

        absolute.unlink()
        escape = self.source / 'escape'
        escape.symlink_to('../../outside')
        with self.assertRaises(ReportTreeSanitizerError):
            ReportTreeSanitizer(self.source, self.destination('escape-out'),
                                self.session).sanitize()
        self.assertFalse(self.destination('escape-out').exists())

        escape.unlink()
        self.write('a', 'a\n')
        (self.source / 'loop-a').symlink_to('loop-b')
        (self.source / 'loop-b').symlink_to('loop-a')
        (self.source / 'missing').symlink_to('missing-target')
        result = ReportTreeSanitizer(
            self.source, self.destination('internal-links'),
            self.session).sanitize()
        self.assertEqual(result['symlinks_preserved'], 3)
        self.assertEqual(os.readlink(self.destination('internal-links') / 'missing'),
                         'missing-target')

    def test_hard_links_are_preserved_only_inside_destination(self):
        self.session.add_hostname('node')
        self.write('node/a.log', 'node 10.20.30.40\n')
        os.link(self.source / 'node' / 'a.log',
                self.source / 'node' / 'b.log')

        result = ReportTreeSanitizer(
            self.source, self.destination(), self.session).sanitize()

        first = self.destination() / 'host1' / 'a.log'
        second = self.destination() / 'host1' / 'b.log'
        self.assertEqual(result['hardlinks_preserved'], 1)
        self.assertEqual(os.stat(first).st_ino, os.stat(second).st_ino)
        self.assertNotEqual(os.stat(first).st_ino,
                            os.stat(self.source / 'node' / 'a.log').st_ino)
        self.assertEqual(first.read_text(), second.read_text())
        self.assertIn('172.17.0.1', first.read_text())

    def test_special_files_fail_closed(self):
        fifo = self.source / 'pipe'
        os.mkfifo(fifo)
        with self.assertRaises(ReportTreeSanitizerError) as context:
            ReportTreeSanitizer(self.source, self.destination(),
                                self.session).sanitize()
        self.assertEqual(context.exception.summary['special_files_rejected'], 1)
        self.assertFalse(self.destination().exists())

        fifo.unlink()
        for mode in (stat.S_IFSOCK, stat.S_IFBLK, stat.S_IFCHR, 0):
            self.assertEqual(ReportTreeSanitizer._classify_mode(mode),
                             'special')

    def test_regular_file_replaced_by_symlink_before_open_fails_closed(self):
        self.write('regular.txt', 'node\n')
        source_file = self.source / 'regular.txt'

        class ReplacingSanitizer(ReportTreeSanitizer):
            def _open_regular(inner_self, name, parent_fd, observed,
                              require_single_link=False):
                source_file.unlink()
                source_file.symlink_to('/etc/passwd')
                return super()._open_regular(
                    name, parent_fd, observed,
                    require_single_link=require_single_link)

        with self.assertRaises(ReportTreeSanitizerError):
            ReplacingSanitizer(self.source, self.destination(),
                               self.session).sanitize()
        self.assertFalse(self.destination().exists())
        self.assertTrue(source_file.is_symlink())


if __name__ == '__main__':
    unittest.main()
