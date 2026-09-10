import os
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.archiver import SafeReportArchiver, SafeReportArchiverError


class ReportArchiverTests(unittest.TestCase):
    def setUp(self):
        self.source_dir = tempfile.TemporaryDirectory()
        self.output_dir = tempfile.TemporaryDirectory()
        self.source = Path(self.source_dir.name)
        self.output = Path(self.output_dir.name)

    def tearDown(self):
        self.output_dir.cleanup()
        self.source_dir.cleanup()

    def write(self, name, content):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def destination(self, name='sanitized.tar.xz'):
        return self.output / name

    def create(self, name='sanitized.tar.xz', **kwargs):
        destination = self.destination(name)
        SafeReportArchiver(self.source, destination, **kwargs).create()
        self.addCleanup(lambda: destination.exists() and destination.unlink())
        return destination

    def test_tar_xz_reopens_with_canonical_metadata_and_order(self):
        self.write('z.txt', b'z')
        self.write('a/b.txt', b'b')
        self.write('links/.keep', b'')
        (self.source / 'link').symlink_to('a/b.txt')
        (self.source / 'links' / 'current').symlink_to('../a/b.txt')
        archive_path = self.create()
        with tarfile.open(archive_path, 'r:xz') as archive:
            members = archive.getmembers()
            self.assertEqual([member.name for member in members],
                             ['a', 'a/b.txt', 'link', 'links',
                              'links/.keep', 'links/current', 'z.txt'])
            for member in members:
                self.assertFalse(member.name.startswith('/'))
                self.assertNotIn('..', member.name.split('/'))
                self.assertEqual((member.uid, member.gid), (0, 0))
                self.assertEqual((member.uname, member.gname), ('', ''))
                self.assertEqual(member.mtime, 0)
                self.assertEqual(member.pax_headers, {})
                self.assertEqual(stat.S_IMODE(member.mode), member.mode)
            self.assertTrue(members[2].issym())
            self.assertEqual(members[2].linkname, 'a/b.txt')
            self.assertEqual(members[5].linkname, '../a/b.txt')

    def test_source_is_unchanged_and_hardlinks_are_independent_files(self):
        first = self.write('first', b'content')
        second = self.source / 'second'
        os.link(first, second)
        before = {path.relative_to(self.source): path.read_bytes()
                  for path in self.source.iterdir()}
        archive_path = self.create()
        with tarfile.open(archive_path, 'r:xz') as archive:
            self.assertTrue(all(member.isreg() for member in archive))
        after = {path.relative_to(self.source): path.read_bytes()
                 for path in self.source.iterdir()}
        self.assertEqual(before, after)

    def test_unsafe_objects_and_symlinks_fail_closed(self):
        os.mkfifo(self.source / 'pipe')
        with self.assertRaises(SafeReportArchiverError):
            SafeReportArchiver(self.source, self.destination()).create()
        self.assertFalse(self.destination().exists())

        (self.source / 'pipe').unlink()
        (self.source / 'escape').symlink_to('../outside')
        with self.assertRaises(SafeReportArchiverError):
            SafeReportArchiver(self.source, self.destination('escape.tar.xz')) \
                .create()
        self.assertFalse(self.destination('escape.tar.xz').exists())

        for kind in ('character', 'block', 'socket', 'unknown'):
            self.assertEqual(SafeReportArchiver._classify_mode(
                {'character': stat.S_IFCHR, 'block': stat.S_IFBLK,
                 'socket': stat.S_IFSOCK, 'unknown': stat.S_IFMT(0)}[kind]),
                'special')

    def test_limits_and_unsupported_format_fail(self):
        self.write('file', b'1234')
        for kwargs in ({'max_file_size': 3}, {'max_total_size': 3},
                       {'max_members': 0}):
            with self.assertRaises(SafeReportArchiverError):
                SafeReportArchiver(self.source, self.destination(),
                                   **kwargs).create()
            self.assertFalse(self.destination().exists())
        with self.assertRaises(SafeReportArchiverError):
            SafeReportArchiver(self.source, self.destination('x.tar.gz'),
                               output_format='gzip').create()

    def test_existing_destination_and_publication_race_are_non_replacing(self):
        destination = self.destination()
        destination.write_bytes(b'keep')
        self.write('file', b'new')
        with self.assertRaises(SafeReportArchiverError):
            SafeReportArchiver(self.source, destination).create()
        self.assertEqual(destination.read_bytes(), b'keep')

        destination.unlink()

        class RaceArchiver(SafeReportArchiver):
            def _publish_noreplace(inner, staging):
                destination.write_bytes(b'keep-race')
                super()._publish_noreplace(staging)

        with self.assertRaises(SafeReportArchiverError):
            RaceArchiver(self.source, destination).create()
        self.assertEqual(destination.read_bytes(), b'keep-race')

    def test_malformed_source_change_and_failure_cleanup(self):
        self.write('file', b'value')
        source_snapshot = (self.source / 'file').read_bytes()

        class ChangingArchiver(SafeReportArchiver):
            def _open_regular(inner, name, parent_fd, observed):
                path = Path(inner.source) / name
                path.unlink()
                path.symlink_to('/etc/passwd')
                return super()._open_regular(name, parent_fd, observed)

        with self.assertRaises(SafeReportArchiverError):
            ChangingArchiver(self.source, self.destination()).create()
        self.assertFalse(self.destination().exists())
        self.assertTrue((self.source / 'file').is_symlink())
        self.assertEqual(source_snapshot, b'value')

        malformed = self.source / 'not-directory'
        malformed.unlink(missing_ok=True)
        malformed.write_bytes(b'x')
        with self.assertRaises(SafeReportArchiverError):
            SafeReportArchiver(malformed, self.destination('bad.tar.xz')) \
                .create()


if __name__ == '__main__':
    unittest.main()
