import io
import os
import errno
import stat
import tarfile
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from sos.cleaner.archiver import SafeReportArchiver, SafeReportArchiverError
from sos.cleaner.mapping_manifest import SoSMappingManifest
from tests.tools.run_archive_stage import (report_root_name,
                                            sanitized_report_root_name)


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

    def test_regular_mode_formula_preserves_ordinary_bits_and_owner_read(self):
        for original, expected in {
                0o000: 0o400, 0o200: 0o600, 0o400: 0o400,
                0o444: 0o444, 0o600: 0o600, 0o644: 0o644,
                0o755: 0o755, 0o4755: 0o755}.items():
            with self.subTest(mode=oct(original)):
                self.assertEqual(
                    SafeReportArchiver._safe_mode(original), expected)

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

    def test_literal_backslash_member_name_round_trips(self):
        self.write('component\\name/file', b'safe')
        archive_path = self.create()
        with tarfile.open(archive_path, 'r:xz') as archive:
            self.assertIn('component\\name', [m.name for m in archive])
            self.assertIn('component\\name/file',
                          [m.name for m in archive])

    def test_long_pax_names_round_trip_for_directory_file_and_symlink(self):
        directory = 'd' * 90
        filename = 'f' * 110
        linkname = 'l' * 110
        self.write(directory + '/' + filename, b'safe')
        (self.source / directory / ('link-' + 'x' * 100)).symlink_to(
            '../' + linkname)
        archive_path = self.create()
        with tarfile.open(archive_path, 'r:xz') as archive:
            names = [member.name for member in archive]
            self.assertIn(directory, names)
            self.assertIn(directory + '/' + filename, names)
            link = archive.getmember(directory + '/' + ('link-' + 'x' * 100))
            self.assertTrue(link.issym())
            self.assertEqual(link.linkname, '../' + linkname)
            self.assertEqual(link.pax_headers.get('path'), link.name)

    def test_ustar_name_boundary_round_trips(self):
        self.write('a' * 100, b'exact')
        self.write('b' * 101, b'next')
        archive_path = self.create()
        with tarfile.open(archive_path, 'r:xz') as archive:
            self.assertEqual(
                {member.name for member in archive},
                {'a' * 100, 'b' * 101})

    def test_archive_stage_preserves_one_report_root(self):
        source = self.output / 'input.tar.xz'
        with tarfile.open(source, 'w:xz') as archive:
            info = tarfile.TarInfo('sosreport-test-root')
            info.type = tarfile.DIRTYPE
            archive.addfile(info)
            info = tarfile.TarInfo('sosreport-test-root/file')
            info.size = 4
            archive.addfile(info, io.BytesIO(b'data'))
        self.assertEqual(report_root_name(source), 'sosreport-test-root')
        manifest = SoSMappingManifest({
            'hostnames': {'sourcehost': 'host0'}, 'domains': {}, 'ipv4': {},
            'ipv6': {}, 'mac': {}, 'emails': {}, 'usernames': {},
        })
        self.assertEqual(
            sanitized_report_root_name(source, manifest),
            'sosreport-test-root')

    def test_pax_archive_is_deterministic(self):
        self.write('d' * 90 + '/' + 'f' * 110, b'safe')
        first = self.create('first.tar.xz')
        second = self.destination('second.tar.xz')
        SafeReportArchiver(self.source, second).create()
        self.addCleanup(lambda: second.exists() and second.unlink())
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_long_unsafe_names_remain_rejected(self):
        with self.assertRaises(ValueError):
            SafeReportArchiver._member_name('../' + 'x' * 300)
        with self.assertRaises(ValueError):
            SafeReportArchiver._member_name('/' + 'x' * 300)
        source = self.source / ('d' * 90)
        source.mkdir()
        (source / ('link-' + 'x' * 100)).symlink_to('../../' + 'x' * 300)
        with self.assertRaises(SafeReportArchiverError):
            SafeReportArchiver(self.source, self.destination()).create()
        self.assertFalse(self.destination().exists())

    def test_failed_file_write_does_not_double_close_descriptor(self):
        self.write('file', b'content')
        real_close = os.close
        bad_closes = []

        def close(fd):
            try:
                return real_close(fd)
            except OSError as error:
                if error.errno == errno.EBADF:
                    bad_closes.append(fd)
                raise

        with mock.patch('sos.cleaner.archiver.os.close', side_effect=close):
            with mock.patch.object(tarfile.TarFile, 'addfile',
                                   side_effect=ValueError('injected')):
                with self.assertRaises(SafeReportArchiverError):
                    SafeReportArchiver(self.source,
                                       self.destination()).create()
        self.assertEqual(bad_closes, [])

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
