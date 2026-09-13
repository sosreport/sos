import io
import os
import random
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.archive_residual import ReportArchiveResidualError, ReportArchiveResidualValidator
from sos.cleaner.extractor import SafeReportExtractor, SafeReportExtractorError
from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.report_residual import ResidualMatcher
from sos.cleaner.session import SanitizationSession, SessionMappingFrozenError


class Phase24SecurityTests(unittest.TestCase):
    """Bounded adversarial regression cases for the report sanitizer."""

    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.path = Path(self.root.name)

    def tearDown(self):
        self.root.cleanup()

    @staticmethod
    def member(name, kind='file', data=b'safe'):
        member = tarfile.TarInfo(name)
        member.uid = member.gid = 0
        member.uname = member.gname = ''
        member.mtime = 0
        member.mode = 0o644
        if kind == 'directory':
            member.type = tarfile.DIRTYPE
        elif kind == 'symlink':
            member.type = tarfile.SYMTYPE
            member.linkname = data.decode()
        elif kind == 'hardlink':
            member.type = tarfile.LNKTYPE
            member.linkname = 'target'
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
            member.size = len(data)
        return member, None if kind != 'file' else data

    def archive(self, members, name='input.tar.xz'):
        path = self.path / name
        with tarfile.open(path, 'w:xz', format=tarfile.USTAR_FORMAT) as output:
            for member, data in members:
                output.addfile(member, io.BytesIO(data) if data is not None else None)
        return path

    def test_extractor_rejects_empty_dot_and_unicode_traversal_components(self):
        for name in ('', '.', './file', 'dir/./file', 'dir//file'):
            with self.subTest(name=name):
                archive = self.archive([self.member(name)])
                with self.assertRaises(SafeReportExtractorError):
                    SafeReportExtractor(archive, temp_parent=self.path).extract()

        for name in ('．．/outside', '．/outside'):
            archive = self.archive([self.member(name)])
            output = SafeReportExtractor(archive, temp_parent=self.path).extract()
            self.addCleanup(lambda: os.path.lexists(output) and
                            __import__('shutil').rmtree(output))
            self.assertTrue(str(Path(output).resolve()).startswith(
                str(self.path.resolve())))

    def test_extractor_rejects_windows_and_backslash_escape_forms(self):
        for name in ('C:\\Windows\\file', '\\\\server\\share\\file',
                     'dir\\..\\outside', 'dir/..\\outside'):
            with self.subTest(name=name):
                with self.assertRaises(SafeReportExtractorError):
                    SafeReportExtractor(self.archive([self.member(name)])).extract()

    def test_extractor_rejects_all_non_fifo_special_objects_and_hardlinks(self):
        for kind in ('hardlink', 'character', 'block'):
            with self.subTest(kind=kind):
                with self.assertRaises(SafeReportExtractorError):
                    SafeReportExtractor(self.archive([self.member(kind, kind)])).extract()

    def test_extractor_member_and_byte_limits_are_fail_closed(self):
        members = [self.member('file-%d' % index) for index in range(4)]
        with self.assertRaises(SafeReportExtractorError):
            SafeReportExtractor(self.archive(members), max_members=3).extract()
        with self.assertRaises(SafeReportExtractorError):
            SafeReportExtractor(self.archive([self.member('file', data=b'1234')]),
                                max_file_size=3).extract()
        with self.assertRaises(SafeReportExtractorError):
            SafeReportExtractor(self.archive([self.member('file', data=b'1234')]),
                                max_total_size=3).extract()
        self.assertEqual(list(self.path.glob('.sos-report-extract-*')), [])

    def test_mapping_freeze_rejects_each_new_identity_namespace(self):
        session = SanitizationSession(self.path / 'session')
        session.sanitize_line('known@example.test')
        session.freeze_mappings()
        for method, value in (
                ('add_username', 'newuser'), ('add_hostname', 'new.example'),
                ('add_ip', '192.0.2.10'), ('add_ipv6', '2001:db8::10'),
                ('add_mac', '12:34:56:78:90:ab'),
                ('add_email', 'new@example.test')):
            with self.subTest(method=method):
                with self.assertRaises(SessionMappingFrozenError):
                    getattr(session, method)(value)

    def test_secret_redaction_state_is_per_stream_and_manifest_free(self):
        session = SanitizationSession(self.path / 'session')
        first = session.sanitize_line('password=synthetic-secret\n')
        second = session.sanitize_line_with_redactor(
            'ordinary text\n', session.new_stream_redactor())
        self.assertNotIn('synthetic-secret', first)
        self.assertEqual(second, 'ordinary text\n')
        manifest = SoSMappingManifest.from_session(session).raw_mappings()
        self.assertNotIn('synthetic-secret', repr(manifest))

    def test_deterministic_bounded_identity_corpus(self):
        values = []
        randomizer = random.Random(2401)
        alphabet = 'abcXYZ012_-'
        for _ in range(64):
            values.append(''.join(randomizer.choice(alphabet)
                                  for _ in range(randomizer.randrange(1, 18))))
        def run():
            session = SanitizationSession(self.path / ('session-%d' % len(values)),
                                          hostnames=('node.example',),
                                          domains=('example.test',),
                                          usernames=('alice',))
            output = [session.sanitize_line(value + '\n') for value in values]
            return output, session.mapping_manifest().raw_mappings()
        first = run()
        second = run()
        self.assertEqual(first, second)
        self.assertEqual(first[1], second[1])

    def test_final_archive_rejects_unsafe_object_types_and_metadata(self):
        manifest = SoSMappingManifest({namespace: {} for namespace in
                                        SoSMappingManifest.namespaces})
        for kind in ('hardlink', 'fifo', 'character', 'block'):
            with self.subTest(kind=kind):
                with self.assertRaises(ReportArchiveResidualError):
                    ReportArchiveResidualValidator(
                        self.archive([self.member('object', kind)]), manifest
                    ).validate()
        member, data = self.member('file')
        member.mode = stat.S_IWUSR
        with self.assertRaises(ReportArchiveResidualError):
            ReportArchiveResidualValidator(
                self.archive([(member, data)]), manifest).validate()

    def test_final_archive_rejects_all_unsafe_link_targets(self):
        manifest = SoSMappingManifest({namespace: {} for namespace in
                                        SoSMappingManifest.namespaces})
        for target in ('/etc/passwd', '../outside', 'a/../../outside',
                       '\\etc\\passwd', ''):
            with self.subTest(target=target):
                with self.assertRaises(ReportArchiveResidualError):
                    ReportArchiveResidualValidator(
                        self.archive([self.member('link', 'symlink',
                                                  target.encode())]), manifest
                    ).validate()

    def test_residual_matcher_never_accepts_generated_alias_as_original(self):
        mappings = {'hostnames': {'node': 'host0'}, 'domains': {},
                    'ipv4': {}, 'ipv6': {}, 'mac': {}, 'emails': {},
                    'usernames': {}}
        matcher = ResidualMatcher(mappings)
        self.assertTrue(matcher.search('node'))
        self.assertFalse(matcher.search('host0'))


if __name__ == '__main__':
    unittest.main()
