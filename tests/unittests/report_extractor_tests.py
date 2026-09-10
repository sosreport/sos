import io
import os
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.extractor import SafeReportExtractor, SafeReportExtractorError


class ReportExtractorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def archive(self, name='report.tar', mode='w', members=()):
        path = self.root / name
        with tarfile.open(path, mode=mode) as archive:
            for member, content in members:
                if member.isreg() and content is not None:
                    member.size = len(content)
                archive.addfile(member, io.BytesIO(content)
                                if content is not None else None)
        return path

    @staticmethod
    def member(name, kind='file', size=None):
        member = tarfile.TarInfo(name)
        if kind == 'directory':
            member.type = tarfile.DIRTYPE
            member.mode = 0o755
        elif kind == 'symlink':
            member.type = tarfile.SYMTYPE
            member.linkname = '../outside'
        elif kind == 'hardlink':
            member.type = tarfile.LNKTYPE
            member.linkname = 'report/file'
        elif kind == 'fifo':
            member.type = tarfile.FIFOTYPE
        elif kind == 'character':
            member.type = tarfile.CHRTYPE
            member.devmajor = 1
            member.devminor = 3
        elif kind == 'block':
            member.type = tarfile.BLKTYPE
            member.devmajor = 1
            member.devminor = 0
        else:
            member.type = tarfile.REGTYPE
            member.size = len(size) if isinstance(size, bytes) else (size or 0)
            member.mode = 0o644
        return member

    def extract(self, archive, **kwargs):
        output = SafeReportExtractor(archive, **kwargs).extract()
        self.addCleanup(lambda: os.path.exists(output) and
                        __import__('shutil').rmtree(output))
        return Path(output)

    def assert_rejected(self, members, **kwargs):
        archive = self.archive(members=members)
        with self.assertRaises(SafeReportExtractorError) as context:
            SafeReportExtractor(archive, **kwargs).extract()
        self.assertNotIn('../', str(context.exception))
        self.assertNotIn('/etc', str(context.exception))

    def test_tar_extracts_successfully(self):
        members = [(self.member('report', 'directory'), None),
                   (self.member('report/file.txt', size=b'hello'), b'hello')]
        output = self.extract(self.archive(members=members))
        self.assertEqual((output / 'report/file.txt').read_bytes(), b'hello')
        self.assertEqual(SafeReportExtractor(self.root / 'report.tar').summary()
                         ['members_seen'], 0)

    def test_compressed_formats_extract(self):
        for suffix, mode in (('.tar.gz', 'w:gz'), ('.tgz', 'w:gz'),
                             ('.tar.bz2', 'w:bz2'), ('.tar.xz', 'w:xz')):
            with self.subTest(suffix=suffix):
                archive = self.archive('report' + suffix, mode=mode,
                                       members=[(self.member('file'), b'x')])
                output = self.extract(archive)
                self.assertEqual((output / 'file').read_bytes(), b'x')

    def test_path_traversal_and_absolute_paths_rejected(self):
        for name in ('/etc/passwd', '../../etc/passwd',
                     'foo/../../../etc/passwd'):
            with self.subTest(name=name):
                self.assert_rejected([(self.member(name), b'x')])

    def test_duplicate_and_type_conflicts_rejected(self):
        self.assert_rejected([(self.member('same'), b'a'),
                              (self.member('same'), b'b')])
        self.assert_rejected([(self.member('file'), b'a'),
                              (self.member('file/child'), b'b')])

    def test_links_are_rejected_without_following_targets(self):
        for kind in ('symlink', 'hardlink'):
            with self.subTest(kind=kind):
                self.assert_rejected([(self.member('link', kind), None)])

    def test_special_members_are_rejected(self):
        for kind in ('fifo', 'character', 'block'):
            with self.subTest(kind=kind):
                self.assert_rejected([(self.member('special', kind), None)])
        for kind in ('socket', 'unknown'):
            self.assertEqual(SafeReportExtractor._classify_member(
                type('Member', (), {
                    'isdir': lambda self: False, 'isreg': lambda self: False,
                    'issym': lambda self: False, 'islnk': lambda self: False,
                    'isfifo': lambda self: False, 'ischr': lambda self: False,
                    'isblk': lambda self: False})()), 'unknown')

    def test_limits_and_malformed_archive_fail_cleanly(self):
        archive = self.archive(members=[(self.member('file'), b'1234')])
        with self.assertRaises(SafeReportExtractorError):
            SafeReportExtractor(archive, max_file_size=3).extract()
        with self.assertRaises(SafeReportExtractorError):
            SafeReportExtractor(archive, max_total_size=3).extract()
        with self.assertRaises(SafeReportExtractorError):
            SafeReportExtractor(archive, max_members=0).extract()

        malformed = self.root / 'malformed.tar'
        malformed.write_bytes(b'not a tar archive')
        with self.assertRaises(SafeReportExtractorError):
            SafeReportExtractor(malformed).extract()
        self.assertFalse(any(path.name.startswith('.sos-report-extract-')
                             for path in self.root.iterdir()))

    def test_archive_unchanged_and_no_output_escape(self):
        archive = self.archive(members=[(self.member('inside'), b'value')])
        before = archive.read_bytes()
        output = self.extract(archive, temp_parent=self.root)
        self.assertEqual(archive.read_bytes(), before)
        self.assertTrue(str(output).startswith(self.root.as_posix()))
        self.assertFalse((self.root / 'outside').exists())

    def test_modes_are_safe_and_ownership_is_not_restored(self):
        member = self.member('file', size=b'value')
        member.mode = stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX | 0o777
        output = self.extract(self.archive(members=[(member, b'value')]))
        self.assertEqual(stat.S_IMODE((output / 'file').stat().st_mode), 0o666)


if __name__ == '__main__':
    unittest.main()
