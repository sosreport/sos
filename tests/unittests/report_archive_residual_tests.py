import os
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.archive_residual import (ReportArchiveResidualError,
                                          ReportArchiveResidualValidator)
from sos.cleaner.archiver import SafeReportArchiver
from sos.cleaner.mapping_manifest import SoSMappingManifest


class ReportArchiveResidualTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        self.manifest = SoSMappingManifest({
            'hostnames': {'host.example': 'host0'},
            'domains': {'customer.example': 'obfuscateddomain0.example'},
            'ipv4': {'10.20.30.40': '10.0.0.1'},
            'ipv6': {'2001:db8::10': '2001:db8::53'},
            'mac': {'12:34:56:78:90:ab': '53:4f:53:00:00:01'},
            'emails': {'alice@customer.example': 'user0@obfuscateddomain0.example'},
            'usernames': {'alice': 'obfuscateduser0'},
        })

    def tearDown(self):
        self.work.cleanup()

    def archive(self, members):
        path = self.root / 'report.tar.xz'
        with tarfile.open(path, 'w:xz', format=tarfile.USTAR_FORMAT) as out:
            for name, kind, value in members:
                info = tarfile.TarInfo(name)
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                info.mtime = 0
                info.mode = 0o644
                if kind == 'directory':
                    info.type = tarfile.DIRTYPE
                    out.addfile(info)
                elif kind == 'symlink':
                    info.type = tarfile.SYMTYPE
                    info.linkname = value
                    out.addfile(info)
                else:
                    data = value.encode()
                    info.size = len(data)
                    out.addfile(info, __import__('io').BytesIO(data))
        return path

    def assert_rejects(self, members):
        with self.assertRaises(ReportArchiveResidualError):
            ReportArchiveResidualValidator(self.archive(members),
                                           self.manifest).validate()

    def test_known_originals_and_generic_residuals_rejected(self):
        values = ('host.example example 10.20.30.40 2001:db8::10 '
                  '12:34:56:78:90:ab alice@customer.example alice')
        self.assert_rejects([('file', 'file', values)])
        for value in ('Authorization: Bearer secret-token',
                      'eyJheader.payload.signature',
                      'AKIAABCDEFGHIJKLMNOP',
                      '-----BEGIN PRIVATE KEY-----',
                      'password=secret',
                      'someone@else.example', '192.0.2.10',
                      '2001:db8::20', 'aa:bb:cc:dd:ee:ff'):
            self.assert_rejects([('file', 'file', value)])

    def test_names_and_symlink_targets_are_validated(self):
        for members in (
                [('host.example', 'file', 'safe')],
                [('customer.example', 'directory', ''),
                 ('customer.example/file', 'file', 'safe')],
                [('link', 'symlink', 'host.example/file')]):
            self.assert_rejects(members)
        for target in ('/etc/passwd', '../outside'):
            self.assert_rejects([('link', 'symlink', target)])

    def test_clean_aliases_and_markers_pass(self):
        data = ('host0 domain0 10.0.0.1 2001:db8::53 '
                '53:4f:53:00:00:01 user0@obfuscateddomain0.example '
                'acct="obfuscateduser0" [REDACTED_SECRET] '
                '[REDACTED_TOKEN]')
        result = ReportArchiveResidualValidator(
            self.archive([('file', 'file', data)]), self.manifest).validate()
        self.assertEqual(result['members_checked'], 1)
        self.assertEqual(result['regular_files_checked'], 1)

    def test_ipv4_mapped_policy_prefix_variants_pass(self):
        data = ('::ffff:0:0/96 '
                '0:0:0:0:0:ffff:0:0/96 '
                '::ffff:0.0.0.0/96 '
                '::ffff:169.254.0.0/112 '
                '0:0:0:0:0:ffff:a9fe:0/112 '
                '::ffff:127.0.0.0/104 '
                '0:0:0:0:0:ffff:7f00:0/104')
        result = ReportArchiveResidualValidator(
            self.archive([('file', 'file', data)]), self.manifest).validate()
        self.assertEqual(result['regular_files_checked'], 1)

    def test_ipv4_mapped_policy_prefix_near_matches_rejected(self):
        for value in (
                '::ffff:192.0.2.1', '::ffff:c000:0201',
                '::ffff:0:1/96', '::ffff:0:0/95',
                '::ffff:0:0/97', '::ffff:169.254.0.1/112',
                '::ffff:169.254.1.0/112', '::ffff:169.254.0.0/111',
                '::ffff:169.254.0.0/113', '::ffff:127.0.0.1/104',
                '::ffff:127.1.0.0/104', '::ffff:127.0.0.0/103',
                '::ffff:127.0.0.0/105', '::ffff:0:0'):
            with self.subTest(value=value):
                self.assert_rejects([('file', 'file', value)])

    def test_literal_backslash_member_name_passes(self):
        result = ReportArchiveResidualValidator(
            self.archive([('component\\name/file', 'file', 'safe')]),
            self.manifest).validate()
        self.assertEqual(result['regular_files_checked'], 1)

    def test_unexpected_binary_regular_member_is_rejected(self):
        self.assert_rejects([('opaque', 'file', 'safe\x00binary')])

    def test_regular_member_requires_owner_read(self):
        path = self.archive([('file', 'file', 'safe')])
        with tarfile.open(path, 'r:xz') as source:
            member = source.getmember('file')
            member.mode = 0o200
            rewritten = self.root / 'unreadable-mode.tar.xz'
            with tarfile.open(rewritten, 'w:xz', format=tarfile.USTAR_FORMAT) as out:
                out.addfile(member, source.extractfile(member))
        with self.assertRaises(ReportArchiveResidualError):
            ReportArchiveResidualValidator(rewritten, self.manifest).validate()

    def test_structure_and_metadata_are_rejected(self):
        self.assert_rejects([('../escape', 'file', 'safe')])
        self.assert_rejects([('file', 'file', 'safe'),
                             ('file', 'file', 'safe')])
        self.assert_rejects([('link', 'symlink', '../outside')])
        path = self.archive([('file', 'file', 'safe')])
        with tarfile.open(path, 'r:xz') as source:
            member = source.getmember('file')
            member.uid = 1
            rewritten = self.root / 'metadata.tar.xz'
            with tarfile.open(rewritten, 'w:xz', format=tarfile.USTAR_FORMAT) as out:
                out.addfile(member, source.extractfile(member))
        with self.assertRaises(ReportArchiveResidualError):
            ReportArchiveResidualValidator(rewritten, self.manifest).validate()

    def test_archiver_private_artifact_can_be_validated_then_published(self):
        source = self.root / 'tree'
        source.mkdir()
        (source / 'file').write_text('safe', encoding='utf-8')
        destination = self.root / 'out.tar.xz'
        archiver = SafeReportArchiver(source, destination)
        private = archiver.create_private()
        result = ReportArchiveResidualValidator(private, self.manifest).validate()
        self.assertEqual(result['members_checked'], 1)
        archiver.publish_private()
        self.assertTrue(destination.exists())

    def test_private_artifact_replacement_fails_publication(self):
        source = self.root / 'tree'
        source.mkdir()
        (source / 'file').write_text('safe', encoding='utf-8')
        destination = self.root / 'out.tar.xz'
        archiver = SafeReportArchiver(source, destination)
        private = Path(archiver.create_private())
        replacement = self.root / 'replacement'
        replacement.write_bytes(b'not the validated archive')
        os.replace(replacement, private)
        with self.assertRaises(Exception):
            archiver.publish_private()
        self.assertFalse(destination.exists())
        archiver.discard_private()


if __name__ == '__main__':
    unittest.main()
