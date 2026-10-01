import gzip
import os
import struct
import tempfile
import unittest

from sos.cleaner.acpi import APPROVED_PATHS, classify_fd as classify_acpi, is_path as is_acpi_path
from sos.cleaner.corosync import PacemakerLog
from sos.cleaner.sssd import SssdLog
from sos.cleaner.systemd import classify_fd as classify_systemd, is_path as is_systemd_path


class RemainingArtifactTests(unittest.TestCase):
    def _regular(self, data):
        directory = tempfile.TemporaryDirectory(prefix='remaining-artifact-')
        path = os.path.join(directory.name, 'object')
        with open(path, 'wb') as stream:
            stream.write(data)
        fd = os.open(path, os.O_RDONLY)
        return directory, fd, os.fstat(fd)

    def test_pacemaker_log_path_is_exact_and_calendar_valid(self):
        self.assertTrue(PacemakerLog.is_path(
            ('var', 'log', 'pacemaker', 'pacemaker.log-20240229.gz')))
        self.assertFalse(PacemakerLog.is_path(
            ('var', 'log', 'pacemaker', 'pacemaker.log-20230229.gz')))
        self.assertFalse(PacemakerLog.is_path(
            ('var', 'log', 'pacemaker', 'pacemaker.log.1.gz')))

    def test_sssd_log_is_exact_and_bounded(self):
        payload = b'KCM diagnostic text\n'
        encoded = gzip.compress(payload, mtime=0)
        directory, fd, observed = self._regular(encoded)
        try:
            with os.fdopen(fd, 'rb', closefd=True) as stream:
                self.assertEqual(SssdLog.classify(stream, observed.st_size),
                                 'omit')
        finally:
            directory.cleanup()
        self.assertFalse(SssdLog.is_path(
            ('var', 'log', 'sssd', 'sssd_nss.log-20260416.gz')))

    def test_acpi_path_set_is_explicit_and_header_checked(self):
        self.assertEqual(len(APPROVED_PATHS), 7)
        path = ('sys', 'firmware', 'acpi', 'tables', 'WAET')
        header = b'WAET' + struct.pack('<I', 40) + b'\0' * 32
        directory, fd, observed = self._regular(header)
        try:
            self.assertTrue(is_acpi_path(path))
            self.assertEqual(classify_acpi(fd, observed, path), 'omit')
        finally:
            os.close(fd)
            directory.cleanup()
        self.assertFalse(is_acpi_path(
            ('sys', 'firmware', 'acpi', 'tables', 'OEMX')))

    def test_systemd_coredump_policy_requires_elf_executable(self):
        header = bytearray(64)
        header[:4] = b'\x7fELF'
        header[4:7] = bytes((2, 1, 1))
        struct.pack_into('<HHIQQQIHHHHHH', header, 16,
                         3, 62, 1, 0, 0, 0, 0, 64, 0, 0, 0, 0, 0)
        directory, fd, observed = self._regular(bytes(header))
        try:
            self.assertTrue(is_systemd_path(
                ('usr', 'lib', 'systemd', 'systemd-coredump')))
            self.assertEqual(classify_systemd(fd, observed), 'omit')
        finally:
            os.close(fd)
            directory.cleanup()
        self.assertFalse(is_systemd_path(
            ('usr', 'lib', 'systemd', 'other-helper')))


if __name__ == '__main__':
    unittest.main()
