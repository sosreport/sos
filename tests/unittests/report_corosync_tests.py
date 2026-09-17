import gzip
import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sos.cleaner.corosync import (CorosyncLog, CorosyncLogError,
                                   PacemakerLog)
from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.report_residual import (ReportTreeResidualError,
                                          ReportTreeResidualValidator)
from sos.cleaner.archive_residual import (ReportArchiveResidualError,
                                           ReportArchiveResidualValidator)
from sos.cleaner.sanitizer import ReportSanitizer
from sos.cleaner.session import SanitizationSession
from sos.cleaner.tree import (ReportTreeSanitizer,
                              ReportTreeSanitizerError)


class CorosyncLogTests(unittest.TestCase):
    def compressed(self, payload):
        return gzip.compress(payload, compresslevel=9, mtime=123)

    def test_exact_calendar_path_grammar(self):
        valid = ('var/log/cluster/corosync.log-20240229.gz',
                 'report/var/log/cluster/corosync.log-20240930.gz')
        invalid = ('var/log/cluster/corosync.log-20230229.gz',
                   'var/log/cluster/corosync.log-20241301.gz',
                   'var/log/cluster/corosync.log-2024011.gz',
                   'var/log/corosync/corosync.log-20240101.gz',
                   'var/log/cluster/corosync.log.1.gz',
                   'report/report/var/log/cluster/corosync.log-20240101.gz')
        for path in valid:
            self.assertTrue(CorosyncLog.is_path(path.split('/')), path)
        for path in invalid:
            self.assertFalse(CorosyncLog.is_path(path.split('/')), path)

    def test_decode_is_strictly_single_bounded_gzip(self):
        payload = b'corosync diagnostic line\n'
        encoded = self.compressed(payload)
        self.assertEqual(CorosyncLog.decode(io.BytesIO(encoded), len(encoded)),
                         payload)
        for bad in (encoded[:-1], encoded + b'trailing',
                    encoded + self.compressed(b'extra')):
            with self.assertRaises(CorosyncLogError):
                CorosyncLog.decode(io.BytesIO(bad), len(bad))
        with self.assertRaises(CorosyncLogError):
            CorosyncLog.decode(io.BytesIO(b'\x1f\x8b\x08bad'), 7)

    def test_strict_utf8_and_deterministic_output(self):
        with tempfile.TemporaryDirectory() as directory:
            session = SanitizationSession(Path(directory) / 'session',
                                          hostnames=('node',),
                                          domains=('example.test',),
                                          usernames=('alice',))
            source = self.compressed(
                b'node 10.20.30.40 alice@example.test password=secret\n')
            sanitized = CorosyncLog.sanitize(
                io.BytesIO(source), len(source), session)
            self.assertNotIn(b'node ', sanitized)
            self.assertNotIn(b'10.20.30.40', sanitized)
            self.assertNotIn(b'secret', sanitized)
            output = CorosyncLog.encode(sanitized)
            self.assertEqual(output, CorosyncLog.encode(sanitized))
            self.assertEqual(output[3], 0)
            self.assertEqual(output[4:8], b'\0\0\0\0')
            self.assertEqual(gzip.decompress(output), sanitized)
            bad = self.compressed(b'bad\xff\n')
            with self.assertRaises(CorosyncLogError):
                CorosyncLog.sanitize(io.BytesIO(bad), len(bad), session)

    def test_limits_are_enforced(self):
        encoded = self.compressed(b'x' * (2 * 1024 * 1024))
        old = (CorosyncLog.MAX_COMPRESSED, CorosyncLog.MAX_DECOMPRESSED,
               CorosyncLog.MAX_RATIO)
        try:
            CorosyncLog.MAX_COMPRESSED = len(encoded) - 1
            with self.assertRaises(CorosyncLogError):
                CorosyncLog.decode(io.BytesIO(encoded), len(encoded))
            CorosyncLog.MAX_COMPRESSED = old[0]
            CorosyncLog.MAX_DECOMPRESSED = 10
            with self.assertRaises(CorosyncLogError):
                CorosyncLog.decode(io.BytesIO(encoded), len(encoded))
            CorosyncLog.MAX_DECOMPRESSED = old[1]
            CorosyncLog.MAX_RATIO = 1
            with self.assertRaises(CorosyncLogError):
                CorosyncLog.decode(io.BytesIO(encoded), len(encoded))
        finally:
            (CorosyncLog.MAX_COMPRESSED, CorosyncLog.MAX_DECOMPRESSED,
             CorosyncLog.MAX_RATIO) = old

    def test_resource_budgets_enforce_member_and_aggregate_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            session = SanitizationSession(Path(directory) / 'session')
            sanitizer = ReportTreeSanitizer(
                directory, Path(directory) / 'output', session)
            old = CorosyncLog.MAX_MEMBERS, CorosyncLog.MAX_AGGREGATE
            try:
                CorosyncLog.MAX_MEMBERS = 2
                CorosyncLog.MAX_AGGREGATE = 1024
                sanitizer._accept_corosync_payload(512)
                sanitizer._accept_corosync_payload(512)
                with self.assertRaises(OSError):
                    sanitizer._accept_corosync_payload(0)
            finally:
                CorosyncLog.MAX_MEMBERS, CorosyncLog.MAX_AGGREGATE = old

            sanitizer._corosync_members = 0
            sanitizer._corosync_bytes = 0
            old_aggregate = CorosyncLog.MAX_AGGREGATE
            try:
                CorosyncLog.MAX_MEMBERS = 10
                CorosyncLog.MAX_AGGREGATE = 1024
                sanitizer._accept_corosync_payload(1024)
                with self.assertRaises(OSError):
                    sanitizer._accept_corosync_payload(1)
            finally:
                CorosyncLog.MAX_AGGREGATE = old_aggregate

    def test_stabilization_discovers_and_freezes_corosync_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            source.mkdir()
            path = source / 'var/log/cluster/corosync.log-20240101.gz'
            path.parent.mkdir(parents=True)
            path.write_bytes(self.compressed(
                b'cluster event user=lateuser\n'))
            session = SanitizationSession(Path(directory) / 'session')

            class ObservedSanitizer(ReportTreeSanitizer):
                def _stabilize_mappings(inner):
                    result = super()._stabilize_mappings()
                    inner.stabilized = inner.session.mapping_manifest()
                    return result

            output = Path(directory) / 'output'
            sanitizer = ObservedSanitizer(source, output, session)
            with mock.patch.object(ReportTreeSanitizer, '_copy_stat'):
                result = sanitizer.sanitize()
            self.assertIn(
                'lateuser', session.username_parser.mapping.dataset)
            self.assertTrue(session.mappings_frozen)
            alias = session.username_parser.mapping.dataset['lateuser']
            content = gzip.decompress(
                (output / 'var/log/cluster/corosync.log-20240101.gz').read_bytes())
            self.assertIn(alias.encode(), content)
            self.assertNotIn(b'lateuser', content)
            self.assertEqual(result['corosync_logs_sanitized'], 1)

    def test_frozen_corosync_mapping_cannot_grow(self):
        with tempfile.TemporaryDirectory() as directory:
            session = SanitizationSession(Path(directory) / 'session')
            session.freeze_mappings()
            before = session.mapping_manifest().raw_mappings()
            encoded = self.compressed(b'user=lateuser\n')
            with self.assertRaises(CorosyncLogError):
                CorosyncLog.sanitize(io.BytesIO(encoded), len(encoded),
                                     session)
            self.assertEqual(session.mapping_manifest().raw_mappings(), before)

    def test_output_residual_callback_rejects_incomplete_sanitization(self):
        with tempfile.TemporaryDirectory() as directory:
            session = SanitizationSession(Path(directory) / 'session')
            sanitizer = ReportTreeSanitizer(
                directory, Path(directory) / 'output', session)
            sanitizer._prepare_corosync_residual_check()
            encoded = self.compressed(b'password=secret\n')

            def incomplete(source, destination, **_kwargs):
                destination.write(source.read())

            with mock.patch('sos.cleaner.corosync.sanitize_stream',
                            side_effect=incomplete):
                with self.assertRaises(CorosyncLogError):
                    CorosyncLog.sanitize(
                        io.BytesIO(encoded), len(encoded), session,
                        residual_check=sanitizer._check_corosync_output_residual)

    def test_pacemaker_residual_error_keeps_safe_category_and_path(self):
        with tempfile.TemporaryDirectory() as directory:
            session = SanitizationSession(
                Path(directory) / 'session', hostnames=('node',))
            session.sanitize_line('node\n')
            sanitizer = ReportTreeSanitizer(
                directory, Path(directory) / 'output', session)
            sanitizer._prepare_corosync_residual_check()
            encoded = self.compressed(b'node\n')
            def incomplete(source, destination, **_kwargs):
                destination.write(source.read())
            with self.assertRaises(CorosyncLogError) as context:
                with mock.patch('sos.cleaner.corosync.sanitize_stream',
                                side_effect=incomplete):
                    PacemakerLog.sanitize(
                        io.BytesIO(encoded), len(encoded), session,
                        residual_check=lambda payload: sanitizer
                        ._check_corosync_output_residual(
                            payload, ('var', 'log', 'pacemaker',
                                      'pacemaker.log-20240101.gz')))
            error = context.exception
            self.assertEqual(error.category, 'known hostname')
            self.assertEqual(error.relative_path,
                             ('var', 'log', 'pacemaker',
                              'pacemaker.log-20240101.gz'))
            self.assertNotIn('node', str(error))

    def test_corosync_source_hardlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            source.mkdir()
            path = source / 'var/log/cluster/corosync.log-20240101.gz'
            path.parent.mkdir(parents=True)
            path.write_bytes(self.compressed(b'safe\n'))
            os.link(path, path.with_name('corosync-copy.gz'))
            with self.assertRaises(ReportTreeSanitizerError):
                ReportTreeSanitizer(
                    source, Path(directory) / 'output',
                    SanitizationSession(Path(directory) / 'session')).sanitize()

    def test_corosync_tree_residual_rejects_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'tree'
            path = root / 'var/log/cluster/corosync.log-20240101.gz'
            path.parent.mkdir(parents=True)
            path.write_bytes(self.compressed(b'password=secret\n'))
            manifest = SoSMappingManifest({
                'hostnames': {}, 'domains': {}, 'ipv4': {}, 'ipv6': {},
                'mac': {}, 'emails': {}, 'usernames': {},
            })
            with self.assertRaises(ReportTreeResidualError):
                ReportTreeResidualValidator(root, manifest).validate()

    def test_corosync_archive_residual_rejects_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / 'report.tar.xz'
            payload = self.compressed(b'token=secret\n')
            with tarfile.open(archive_path, 'w:xz') as archive:
                info = tarfile.TarInfo(
                    'var/log/cluster/corosync.log-20240101.gz')
                info.size = len(payload)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(payload))
            manifest = SoSMappingManifest({
                'hostnames': {}, 'domains': {}, 'ipv4': {}, 'ipv6': {},
                'mac': {}, 'emails': {}, 'usernames': {},
            })
            with self.assertRaises(ReportArchiveResidualError):
                ReportArchiveResidualValidator(archive_path, manifest).validate()

    def test_corosync_oversized_archive_member_rejected_before_body_read(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = SoSMappingManifest({
                'hostnames': {}, 'domains': {}, 'ipv4': {}, 'ipv6': {},
                'mac': {}, 'emails': {}, 'usernames': {},
            })
            validator = ReportArchiveResidualValidator(
                Path(directory) / 'unused.tar.xz', manifest)
            member = tarfile.TarInfo(
                'var/log/cluster/corosync.log-20240101.gz')
            member.size = CorosyncLog.MAX_COMPRESSED + 1

            class NoBodyReadArchive:
                def extractfile(self, _member):
                    raise AssertionError('oversized body was opened')

            with self.assertRaises(ReportArchiveResidualError):
                validator._check_regular(NoBodyReadArchive(), member)

    def test_corosync_pipeline_does_not_modify_source_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input-tree'
            path = source / 'var/log/cluster/corosync.log-20240101.gz'
            path.parent.mkdir(parents=True)
            path.write_bytes(self.compressed(
                b'node-a.example 10.20.30.40 password=secret\n'))
            archive_path = root / 'input.tar.xz'
            with tarfile.open(archive_path, 'w:xz') as archive:
                archive.add(source, arcname='sosreport-input')
            before = archive_path.read_bytes()
            output = root / 'output.tar.xz'
            with mock.patch.object(ReportTreeSanitizer, '_copy_stat'):
                result = ReportSanitizer(
                    hostnames=('node-a.example',), temp_parent=root).sanitize(
                        archive_path, output)
            self.assertEqual(archive_path.read_bytes(), before)
            self.assertEqual(result['tree']['corosync_logs_sanitized'], 1)
            with tarfile.open(output, 'r:xz') as archive:
                member = archive.getmember(
                    'sosreport-input/var/log/cluster/corosync.log-20240101.gz')
                content = gzip.decompress(archive.extractfile(member).read())
            self.assertNotIn(b'node-a.example', content)
            self.assertNotIn(b'secret', content)

    def test_tree_residual_rejects_compressed_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'tree'
            path = root / 'var/log/cluster/corosync.log-20240101.gz'
            path.parent.mkdir(parents=True)
            path.write_bytes(self.compressed(b'original-host\n'))
            manifest = SoSMappingManifest.from_session(
                SanitizationSession(Path(directory) / 'session',
                                    hostnames=('original-host',)))
            with self.assertRaises(ReportTreeResidualError):
                ReportTreeResidualValidator(root, manifest).validate()

    def test_archive_residual_rejects_compressed_original(self):
        import tarfile
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / 'report.tar.xz'
            payload = self.compressed(b'original-host\n')
            with tarfile.open(archive_path, 'w:xz') as archive:
                info = tarfile.TarInfo(
                    'var/log/cluster/corosync.log-20240101.gz')
                info.size = len(payload)
                info.mode = 0o644
                info.uid = info.gid = info.mtime = 0
                archive.addfile(info, io.BytesIO(payload))
            manifest = SoSMappingManifest.from_session(
                SanitizationSession(Path(directory) / 'session',
                                    hostnames=('original-host',)))
            with self.assertRaises(ReportArchiveResidualError):
                ReportArchiveResidualValidator(archive_path, manifest).validate()


if __name__ == '__main__':
    unittest.main()
