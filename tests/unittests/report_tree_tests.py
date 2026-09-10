import os
import stat
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.discovery import ReportIdentityDiscovery
from sos.cleaner.session import SanitizationSession
from sos.cleaner.tree import ReportTreeSanitizer, ReportTreeSanitizerError


class ReportTreeTests(unittest.TestCase):
    def setUp(self):
        self.source_dir = tempfile.TemporaryDirectory()
        self.session_dir = tempfile.TemporaryDirectory()
        self.output_parent = tempfile.TemporaryDirectory()
        self.source = Path(self.source_dir.name)
        self.session = SanitizationSession(
            self.session_dir.name,
            hostnames=('seedhost',), domains=('sensitive.example',),
            usernames=('alice',))

    def tearDown(self):
        self.output_parent.cleanup()
        self.session_dir.cleanup()
        self.source_dir.cleanup()

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
            def _open_regular(inner_self, name, parent_fd, observed):
                source_file.unlink()
                source_file.symlink_to('/etc/passwd')
                return super()._open_regular(name, parent_fd, observed)

        with self.assertRaises(ReportTreeSanitizerError):
            ReplacingSanitizer(self.source, self.destination(),
                               self.session).sanitize()
        self.assertFalse(self.destination().exists())
        self.assertTrue(source_file.is_symlink())


if __name__ == '__main__':
    unittest.main()
