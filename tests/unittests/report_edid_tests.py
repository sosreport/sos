import os
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.edid import DrmEdidPolicy
from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.report_residual import (ReportTreeResidualError,
                                          ReportTreeResidualValidator)
from sos.cleaner.archive_residual import (ReportArchiveResidualError,
                                           ReportArchiveResidualValidator)
from sos.cleaner.session import SanitizationSession
from sos.cleaner.tree import ReportTreeSanitizer


def make_edid(blocks=1, checksum=True):
    data = bytearray(blocks * 128)
    data[:8] = b'\x00\xff\xff\xff\xff\xff\xff\x00'
    data[126] = blocks - 1
    data[12:16] = b'LAB1'
    for offset in range(0, len(data), 128):
        data[offset + 127] = (-sum(data[offset:offset + 127])) & 0xff
    if not checksum:
        data[127] ^= 1
    return bytes(data)


class ReportEdidTests(unittest.TestCase):
    def test_exact_path_grammar(self):
        valid = (
            'sys/class/drm/card0-DP-1/edid',
            'sys/class/drm/card0-HDMI-A-1/edid',
            'sys/class/drm/card0-DP-1-1/edid',
            'sys/devices/pci0000:00/0000:00:01.0/drm/card0/'
            'card0-Virtual-1/edid',
            'report/sys/class/drm/card12-DP-1/edid',
        )
        invalid = (
            'sys/foo/edid', 'sys/class/drm/card0-DP-1/edid_override',
            'sys/class/drm/card0-DP-1/extra/edid',
            'sys/devices/pci/drm/card1/card0-DP-1/edid',
            'report/report/sys/class/drm/card0-DP-1/edid',
            'sys/class/drm/card0-DP-/edid',
        )
        for path in valid:
            self.assertTrue(DrmEdidPolicy.is_path(path.split('/')), path)
        for path in invalid:
            self.assertFalse(DrmEdidPolicy.is_path(path.split('/')), path)

    def classify(self, payload):
        with tempfile.NamedTemporaryFile() as handle:
            handle.write(payload)
            handle.flush()
            fd = os.open(handle.name, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                return DrmEdidPolicy.classify_fd(fd, os.fstat(fd))
            finally:
                os.close(fd)

    def test_size_and_structure_boundaries(self):
        self.assertEqual(self.classify(b''), 'omit')
        for size in (1, 127, 129, 4097):
            self.assertEqual(self.classify(b'X' * size), 'reject')
        self.assertEqual(self.classify(make_edid(1)), 'omit')
        self.assertEqual(self.classify(make_edid(2)), 'omit')
        self.assertEqual(self.classify(make_edid(32)), 'omit')

    def test_header_and_extension_count_are_required(self):
        data = bytearray(make_edid())
        data[0] = 1
        self.assertEqual(self.classify(data), 'reject')
        data = bytearray(make_edid(2))
        data[126] = 0
        self.assertEqual(self.classify(data), 'reject')

    def test_bad_checksums_are_omitted(self):
        self.assertEqual(self.classify(make_edid(checksum=False)), 'omit')

    def test_classification_does_not_modify_source_bytes(self):
        payload = make_edid(2, checksum=False)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'edid'
            path.write_bytes(payload)
            before = path.read_bytes()
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                self.assertEqual(DrmEdidPolicy.classify_fd(fd, os.fstat(fd)),
                                 'omit')
            finally:
                os.close(fd)
            link = Path(directory) / 'hard'
            os.link(path, link)
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                self.assertEqual(DrmEdidPolicy.classify_fd(fd, os.fstat(fd)),
                                 'reject')
            finally:
                os.close(fd)
            self.assertEqual(path.read_bytes(), before)

    def test_object_predicate_requires_single_regular_link(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'edid'
            path.write_bytes(make_edid())
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                observed = os.fstat(fd)
                self.assertEqual(DrmEdidPolicy.classify_fd(fd, observed),
                                 'omit')
            finally:
                os.close(fd)

    def test_tree_omits_before_text_or_binary_probes_and_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            path = source / 'sys/class/drm/card0-DP-1/edid'
            path.parent.mkdir(parents=True)
            path.write_bytes(make_edid(2, checksum=False))
            session_dir = Path(directory) / 'session'
            session_dir.mkdir()
            session = SanitizationSession(session_dir)
            sanitizer = ReportTreeSanitizer(source, Path(directory) / 'out',
                                             session)
            sanitizer._is_text_fd = lambda fd: self.fail('text probe called')
            sanitizer._binary_omission_class = lambda relative, fd: self.fail(
                'generic binary probe called')
            parent_fd = os.open(path.parent, os.O_RDONLY)
            try:
                sanitizer._copy_file('edid', parent_fd, path.stat(),
                                     Path(directory) / 'out' / 'edid',
                                     tuple(path.relative_to(source).parts))
            finally:
                os.close(parent_fd)
            self.assertEqual(sanitizer.summary()['display_edids_omitted'], 1)
            self.assertEqual(sanitizer.summary()['binary_files_omitted'], 1)
            self.assertFalse((Path(directory) / 'out' / 'edid').exists())

    def test_tree_residual_rejects_any_approved_edid_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'tree'
            path = source / 'sys/class/drm/card0-DP-1/edid'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'placeholder')
            session = SanitizationSession(Path(directory) / 'session')
            manifest = SoSMappingManifest.from_session(session)
            with self.assertRaises(ReportTreeResidualError):
                ReportTreeResidualValidator(source, manifest).validate()

    def test_archive_residual_rejects_any_approved_edid_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / 'report.tar.xz'
            with tarfile.open(archive_path, 'w:xz') as archive:
                info = tarfile.TarInfo('sys/class/drm/card0-DP-1/edid')
                info.size = 0
                info.mode = 0o644
                info.uid = info.gid = info.mtime = 0
                archive.addfile(info, io.BytesIO())
            session = SanitizationSession(Path(directory) / 'session')
            manifest = SoSMappingManifest.from_session(session)
            with self.assertRaises(ReportArchiveResidualError):
                ReportArchiveResidualValidator(archive_path, manifest).validate()


if __name__ == '__main__':
    unittest.main()
