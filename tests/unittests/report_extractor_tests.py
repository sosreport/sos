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
    def member(name, kind='file', size=None, linkname=None):
        member = tarfile.TarInfo(name)
        if kind == 'directory':
            member.type = tarfile.DIRTYPE
            member.mode = 0o755
        elif kind == 'symlink':
            member.type = tarfile.SYMTYPE
            member.linkname = '../outside' if linkname is None else linkname
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
                     'foo/../../../etc/passwd', '..\\etc\\passwd',
                     'foo\\..\\bar', 'C:\\Windows\\file',
                     '\\etc\\passwd', '\\\\server\\share\\file'):
            with self.subTest(name=name):
                self.assert_rejected([(self.member(name), b'x')])

    def test_literal_backslashes_are_preserved_and_not_path_separators(self):
        members = [(self.member('foo\\bar'), b'literal'),
                   (self.member('foo/bar'), b'slash'),
                   (self.member('component\\name/file'), b'nested')]
        output = self.extract(self.archive(members=members))
        self.assertEqual((output / 'foo\\bar').read_bytes(), b'literal')
        self.assertEqual((output / 'foo/bar').read_bytes(), b'slash')
        self.assertEqual((output / 'component\\name/file').read_bytes(),
                         b'nested')

    def test_backslash_member_names_are_not_collapsed_into_collisions(self):
        members = [(self.member('foo\\bar'), b'backslash'),
                   (self.member('foo/bar'), b'slash')]
        output = self.extract(self.archive(members=members))
        self.assertEqual(len(list(output.rglob('*'))), 3)
        self.assertNotEqual((output / 'foo\\bar').read_bytes(),
                            (output / 'foo/bar').read_bytes())

    def test_duplicate_and_type_conflicts_rejected(self):
        self.assert_rejected([(self.member('same'), b'a'),
                              (self.member('same'), b'b')])
        self.assert_rejected([(self.member('file'), b'a'),
                              (self.member('file/child'), b'b')])

    def test_internal_relative_symlink_is_preserved_without_following(self):
        members = [(self.member('report', 'directory'), None),
                   (self.member('report/target', size=b'value'), b'value'),
                   (self.member('report/link', 'symlink',
                                linkname='target'), None)]
        output = self.extract(self.archive(members=members))
        link = output / 'report/link'
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), 'target')
        self.assertEqual(link.readlink().name, 'target')
        self.assertEqual(SafeReportExtractor(
            self.root / 'report.tar').summary()['symlinks_created'], 0)

    def test_internal_dangling_symlink_is_preserved(self):
        members = [(self.member('report', 'directory'), None),
                   (self.member('report/link', 'symlink',
                                linkname='missing'), None)]
        output = self.extract(self.archive(members=members))
        self.assertEqual(os.readlink(output / 'report/link'), 'missing')

    def test_unsafe_symlinks_are_rejected(self):
        for target in ('/etc/passwd', '../../outside', 'foo/../../../outside'):
            with self.subTest(target=target):
                self.assert_rejected([(self.member(
                    'report/link', 'symlink', linkname=target), None)])

    def test_symlink_is_not_an_extraction_directory(self):
        members = [(self.member('report', 'directory'), None),
                   (self.member('report/link', 'symlink',
                                linkname='target'), None),
                   (self.member('report/link/file'), b'unsafe')]
        self.assert_rejected(members)

    def test_hardlinks_remain_rejected(self):
        self.assert_rejected([(self.member('link', 'hardlink'), None)])

    def test_fifo_is_omitted_and_counted(self):
        archive = self.archive(members=[(self.member('report', 'directory'),
                                         None),
                                        (self.member('report/pipe', 'fifo'),
                                         None),
                                        (self.member('report/file'), b'value')])
        extractor = SafeReportExtractor(archive, temp_parent=self.root)
        output = Path(extractor.extract())
        self.addCleanup(lambda: os.path.exists(output) and
                        __import__('shutil').rmtree(output))
        self.assertEqual(extractor.summary()['fifos_omitted'], 1)
        self.assertFalse((output / 'report/pipe').exists())
        self.assertFalse((output / 'report/pipe').is_fifo())
        self.assertTrue((output / 'report/file').is_file())

    def test_fifo_conflicts_fail_closed(self):
        cases = [
            [(self.member('pipe', 'fifo'), None),
             (self.member('pipe'), b'value')],
            [(self.member('pipe', 'fifo'), None),
             (self.member('pipe/child'), b'value')],
            [(self.member('pipe', 'fifo'), None),
             (self.member('pipe/child', 'directory'), None)],
        ]
        for members in cases:
            with self.subTest():
                self.assert_rejected(members)

    def test_member_type_conflicts_fail_closed(self):
        cases = [
            [(self.member('path', 'directory'), None),
             (self.member('path', 'symlink', linkname='target'), None)],
            [(self.member('path', 'symlink', linkname='target'), None),
             (self.member('path', 'directory'), None)],
            [(self.member('path', 'symlink', linkname='target'), None),
             (self.member('path'), b'value')],
            [(self.member('path', 'directory'), None),
             (self.member('path', 'symlink', linkname='target'), None)],
            [(self.member('path', 'symlink', linkname='target'), None),
             (self.member('path', 'symlink', linkname='target'), None)],
        ]
        for members in cases:
            with self.subTest():
                self.assert_rejected(members)

    def test_special_members_are_rejected(self):
        for kind in ('character', 'block'):
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
        self.assertEqual(stat.S_IMODE((output / 'file').stat().st_mode), 0o777)

    def test_read_only_directories_are_finalized_after_children(self):
        parent = self.member('parent', 'directory')
        parent.mode = 0o555
        nested = self.member('parent/nested', 'directory')
        nested.mode = 0o500
        output = self.extract(self.archive(members=[
            (parent, None), (nested, None),
            (self.member('parent/nested/file', size=b'value'), b'value')]))
        self.addCleanup(lambda: os.chmod(output / 'parent/nested', 0o700))
        self.addCleanup(lambda: os.chmod(output / 'parent', 0o700))
        self.assertEqual(stat.S_IMODE((output / 'parent').stat().st_mode),
                         0o555)
        self.assertEqual(stat.S_IMODE(
            (output / 'parent/nested').stat().st_mode), 0o500)
        self.assertEqual((output / 'parent/nested/file').read_bytes(),
                         b'value')

    def test_non_searchable_directory_mode_is_applied_only_at_end(self):
        parent = self.member('parent', 'directory')
        parent.mode = 0o444
        output = self.extract(self.archive(members=[
            (parent, None), (self.member('parent/file'), b'value')]))
        self.addCleanup(lambda: os.chmod(output / 'parent', 0o700))
        self.assertEqual(stat.S_IMODE((output / 'parent').stat().st_mode),
                         0o444)

    def test_regular_file_modes_are_applied_after_writing(self):
        expected = {
            0o000: 0o400,
            0o200: 0o600,
            0o400: 0o400,
            0o444: 0o444,
            0o600: 0o600,
            0o644: 0o644,
            0o755: 0o755,
        }
        for mode, final_mode in expected.items():
            with self.subTest(mode=oct(mode)):
                member = self.member('file', size=b'value')
                member.mode = mode
                output = self.extract(self.archive(members=[(member, b'value')]))
                self.assertEqual(stat.S_IMODE((output / 'file').stat().st_mode),
                                 final_mode)

    def test_regular_file_construction_mode_is_private(self):
        observed_modes = []

        class ModeProbe(SafeReportExtractor):
            @staticmethod
            def _write_all(fd, data):
                observed_modes.append(stat.S_IMODE(os.fstat(fd).st_mode))
                return SafeReportExtractor._write_all(fd, data)

        output = ModeProbe(
            self.archive(members=[(self.member('file'), b'value')])).extract()
        self.addCleanup(lambda: os.path.exists(output) and
                        __import__('shutil').rmtree(output))
        self.assertEqual(observed_modes, [0o600])
        self.assertEqual(stat.S_IMODE((Path(output) / 'file').stat().st_mode),
                         0o644)

    def test_zero_length_mode_zero_is_validated_and_owner_readable(self):
        member = self.member('empty', size=b'')
        member.mode = 0o000
        output = self.extract(self.archive(members=[(member, b'')]))
        empty = Path(output) / 'empty'
        self.assertEqual(empty.stat().st_size, 0)
        self.assertEqual(stat.S_IMODE(empty.stat().st_mode), 0o400)

    def test_extraction_root_stays_private(self):
        output = self.extract(self.archive(members=[
            (self.member('file'), b'value')]))
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)

    def test_directory_finalization_failure_cleans_staging(self):
        class FailingFinalizer(SafeReportExtractor):
            def _finalize_directory_modes(inner, root_fd, directory_modes):
                super()._finalize_directory_modes(root_fd, directory_modes)
                raise OSError('finalization failed')

        archive = self.archive(members=[
            (self.member('parent', 'directory'), None),
            (self.member('parent/file'), b'value')])
        with self.assertRaises(SafeReportExtractorError):
            FailingFinalizer(archive, temp_parent=self.root).extract()
        self.assertFalse(any(path.name.startswith('.sos-report-extract-')
                             for path in self.root.iterdir()))


if __name__ == '__main__':
    unittest.main()
