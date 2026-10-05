import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.archive_residual import ReportArchiveResidualValidator
from sos.cleaner.archiver import SafeReportArchiver
from sos.cleaner.extractor import SafeReportExtractor
from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.sanitizer import ReportSanitizer
from sos.cleaner.session import SanitizationSession
from sos.cleaner.symlink import validate_symlink_target
from sos.cleaner.tree import ReportTreeSanitizer, ReportTreeSanitizerError


class Phase25SymlinkTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)

    def tearDown(self):
        self.work.cleanup()

    @staticmethod
    def member(name, kind='file', linkname=None, data=b''):
        info = tarfile.TarInfo(name)
        if kind == 'directory':
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
        elif kind == 'symlink':
            info.type = tarfile.SYMTYPE
            info.linkname = linkname
        else:
            info.type = tarfile.REGTYPE
            info.mode = 0o644
            info.size = len(data)
        return info, data

    def archive(self, members, name='input.tar.xz'):
        path = self.root / name
        with tarfile.open(path, 'w:xz', format=tarfile.USTAR_FORMAT) as out:
            for info, data in members:
                out.addfile(info, io.BytesIO(data) if info.isreg() else None)
        return path

    def assert_target(self, target, member='report/dir/link'):
        return validate_symlink_target(member, target)

    def test_target_policy_matrix(self):
        passing = ('../safe\\x2dname', r'foo\bar', './foo',
                   'foo/../bar', 'foo//bar', 'missing')
        for target in passing:
            with self.subTest(target=target):
                self.assertEqual(self.assert_target(target), target)

        failing = ('/absolute/path', '../../escape', '../../../escape',
                   r'C:\Windows\file', 'C:/Windows/file', 'C:relative',
                   r'\\server\share', r'\absolute-like', r'..\outside',
                   r'dir\..\outside', r'dir/..\outside', r'dir\../outside',
                   '', 'bad\x00target')
        for target in failing:
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    self.assert_target(target, 'report/link')

    def test_extractor_accepts_literal_systemd_target_without_dereference(
            self):
        root = 'report'
        target_name = root + (
            r'/run/systemd/generator/dev-mapper-rhel\x2dswap.swap')
        link_name = root + (
            r'/run/systemd/generator/swap.target.requires/'
            r'dev-mapper-rhel\x2dswap.swap')
        members = [self.member(root, 'directory')]
        for directory in (
                root + '/run', root + '/run/systemd',
                root + '/run/systemd/generator',
                root + '/run/systemd/generator/swap.target.requires'):
            members.append(self.member(directory, 'directory'))
        members.extend((self.member(target_name, data=b'unit'),
                        self.member(link_name, 'symlink',
                                    linkname=(
                                        r'../dev-mapper-rhel\x2dswap.swap'))))
        extractor = SafeReportExtractor(self.archive(members),
                                        temp_parent=self.root)
        extracted = Path(extractor.extract())
        self.addCleanup(lambda: os.path.lexists(extracted) and
                        __import__('shutil').rmtree(extracted))
        link = extracted / link_name
        self.assertEqual(os.readlink(link), r'../dev-mapper-rhel\x2dswap.swap')
        self.assertTrue((extracted / target_name).is_file())

    def test_systemd_style_case_round_trips_end_to_end(self):
        root = 'sosreport-input'
        target_name = root + (
            r'/run/systemd/generator/dev-mapper-rhel\x2dswap.swap')
        link_name = root + (
            r'/run/systemd/generator/swap.target.requires/'
            r'dev-mapper-rhel\x2dswap.swap')
        members = [self.member(root, 'directory')]
        for directory in (
                root + '/run', root + '/run/systemd',
                root + '/run/systemd/generator',
                root + '/run/systemd/generator/swap.target.requires'):
            members.append(self.member(directory, 'directory'))
        members.extend((self.member(target_name, data=b'unit'),
                        self.member(link_name, 'symlink',
                                    linkname=(
                                        r'../dev-mapper-rhel\x2dswap.swap'))))
        output = self.root / 'sanitized.tar.xz'
        ReportSanitizer(temp_parent=self.root).sanitize(
            self.archive(members), output)
        with tarfile.open(output, 'r:xz') as archive:
            link = archive.getmember(link_name)
            self.assertTrue(link.issym())
            self.assertEqual(link.linkname,
                             r'../dev-mapper-rhel\x2dswap.swap')

    def test_tree_rewrite_checks_source_target_policy(self):
        session_dir = tempfile.TemporaryDirectory()
        self.addCleanup(session_dir.cleanup)
        sanitizer = ReportTreeSanitizer(
            self.root, self.root / 'destination',
            SanitizationSession(session_dir.name))
        self.assertEqual(
            sanitizer._rewrite_symlink_target(r'../safe\x2dname',
                                               ('report', 'dir'), 'link'),
            r'../safe\x2dname')
        with self.assertRaises(ReportTreeSanitizerError):
            sanitizer._rewrite_symlink_target(r'dir/..\outside',
                                              ('report',), 'link')

    def test_structural_policy_is_equivalent_across_components(self):
        session_dir = tempfile.TemporaryDirectory()
        self.addCleanup(session_dir.cleanup)
        tree = ReportTreeSanitizer(
            self.root, self.root / 'destination',
            SanitizationSession(session_dir.name))
        passing = ('../safe\\x2dname', r'foo\bar', './foo',
                   'foo/../bar', 'foo//bar')
        failing = ('/absolute/path', '../../escape', 'C:/Windows/file',
                   r'..\outside', r'dir/..\outside', '')
        for expected, targets in ((True, passing), (False, failing)):
            for target in targets:
                with self.subTest(target=target):
                    outcomes = []
                    for check in (
                            lambda: validate_symlink_target(
                                'report/link', target),
                            lambda: SafeReportArchiver._validate_link_target(
                                target, 'report'),
                            lambda: ReportArchiveResidualValidator
                            ._validate_link_target(target, 'report/link'),
                            lambda: tree._rewrite_symlink_target(
                                target, ('report',), 'link')):
                        try:
                            check()
                            outcomes.append(True)
                        except (ValueError, ReportTreeSanitizerError):
                            outcomes.append(False)
                    self.assertEqual(outcomes, [expected] * 4)

    def test_archiver_and_archive_residual_accept_literal_target(self):
        source = self.root / 'report'
        source.mkdir()
        (source / r'dev-mapper-rhel\x2dswap.swap').write_bytes(b'unit')
        (source / 'requires').mkdir()
        (source / 'requires' / 'link').symlink_to(
            r'../dev-mapper-rhel\x2dswap.swap')
        destination = self.root / 'output.tar.xz'
        SafeReportArchiver(source, destination).create()
        manifest = SoSMappingManifest({
            'hostnames': {}, 'domains': {}, 'ipv4': {}, 'ipv6': {},
            'mac': {}, 'emails': {}, 'usernames': {},
        })
        ReportArchiveResidualValidator(destination, manifest).validate()
        with tarfile.open(destination, 'r:xz') as archive:
            link = archive.getmember('requires/link')
            self.assertEqual(link.linkname,
                             r'../dev-mapper-rhel\x2dswap.swap')

    def test_internal_loops_and_dangling_targets_are_not_dereferenced(self):
        source = self.root / 'report'
        source.mkdir()
        (source / 'loop-a').symlink_to('loop-b')
        (source / 'loop-b').symlink_to('loop-a')
        (source / 'dangling').symlink_to('missing')
        destination = self.root / 'output.tar.xz'
        SafeReportArchiver(source, destination).create()
        with tarfile.open(destination, 'r:xz') as archive:
            self.assertEqual(archive.getmember('loop-a').linkname, 'loop-b')
            self.assertEqual(archive.getmember('dangling').linkname, 'missing')


if __name__ == '__main__':
    unittest.main()
