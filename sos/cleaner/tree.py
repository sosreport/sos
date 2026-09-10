# This file is part of the sos project: https://github.com/sosreport/sos

"""Sanitization of an already-extracted report directory."""

import codecs
import ctypes
import errno
import os
import shutil
import tempfile

from sos.cleaner.text import sanitize_stream
from sos.utilities import file_is_binary


class ReportTreeSanitizerError(Exception):
    """A safe tree-sanitization failure carrying counts only."""

    def __init__(self, summary):
        self.summary = dict(summary)
        super().__init__('report tree sanitization failed')


class ReportTreeSanitizer:
    """Build a sanitized destination tree using one shared session."""

    def __init__(self, source, destination, session):
        self.source = os.path.abspath(source)
        self.destination = os.path.abspath(destination)
        self.session = session
        self._summary = {
            'files_processed': 0,
            'directories_created': 0,
            'paths_renamed': 0,
            'text_files_sanitized': 0,
            'unsupported_files': 0,
            'failures': 0,
        }

    def sanitize(self):
        """Publish a complete sanitized tree or raise without publishing."""
        self._validate_roots()
        parent = os.path.dirname(self.destination)
        if not os.path.isdir(parent):
            self._fail()
        if os.path.lexists(self.destination):
            self._fail()
        staging = tempfile.mkdtemp(prefix='.sos-report-sanitize-', dir=parent)
        try:
            self._summary['directories_created'] += 1
            self._copy_directory(self.source, staging)
            shutil.copystat(self.source, staging, follow_symlinks=False)
            if os.path.lexists(self.destination):
                self._fail()
            self._publish_noreplace(staging)
            if not os.path.isdir(self.destination):
                self._fail()
            return dict(self._summary)
        except ReportTreeSanitizerError:
            raise
        except Exception:
            self._fail()
        finally:
            if os.path.lexists(staging):
                shutil.rmtree(staging, ignore_errors=True)

    def summary(self):
        """Return counts only for the current operation."""
        return dict(self._summary)

    def _fail(self):
        self._summary['failures'] += 1
        raise ReportTreeSanitizerError(self._summary)

    def _validate_roots(self):
        if not os.path.isdir(self.source) or os.path.islink(self.source):
            self._fail()
        source_real = os.path.realpath(self.source)
        destination_real = os.path.realpath(self.destination)
        try:
            if os.path.commonpath((source_real, destination_real)) == source_real:
                self._fail()
        except ValueError:
            self._fail()

    def _publish_noreplace(self, staging):
        """Atomically publish a directory without replacing a destination.

        Python has no portable atomic rename-no-replace API. sos runs on
        Linux, where renameat2 with RENAME_NOREPLACE provides the required
        guarantee. Platforms without that primitive fail closed instead of
        falling back to an unsafe check-then-rename sequence.
        """
        if os.name != 'posix':
            raise OSError(errno.ENOTSUP, 'atomic no-replace publish unavailable')
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            renameat2 = libc.renameat2
        except (AttributeError, OSError):
            raise OSError(errno.ENOTSUP,
                          'atomic no-replace publish unavailable') from None
        renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p,
                              ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100, os.fsencode(staging), -100, os.fsencode(self.destination), 1
        )
        if result != 0:
            error = ctypes.get_errno()
            raise OSError(error, 'atomic no-replace publish failed')

    def _sanitized_name(self, name):
        result = self.session.sanitize_known_text(name)
        if not result or result in ('.', '..') or os.sep in result:
            self._fail()
        if os.altsep and os.altsep in result:
            self._fail()
        if result != name:
            self._summary['paths_renamed'] += 1
        return result

    def _copy_directory(self, source, destination):
        try:
            entries = sorted(os.scandir(source), key=lambda entry: entry.name)
        except Exception:
            self._fail()
        seen = set()
        for entry in entries:
            name = self._sanitized_name(entry.name)
            if name in seen or os.path.lexists(os.path.join(destination, name)):
                self._fail()
            seen.add(name)
            source_path = entry.path
            destination_path = os.path.join(destination, name)
            try:
                if entry.is_symlink():
                    self._summary['unsupported_files'] += 1
                    self._fail()
                if entry.is_dir(follow_symlinks=False):
                    os.mkdir(destination_path)
                    self._summary['directories_created'] += 1
                    self._copy_directory(source_path, destination_path)
                    shutil.copystat(source_path, destination_path,
                                    follow_symlinks=False)
                elif entry.is_file(follow_symlinks=False):
                    self._copy_file(source_path, destination_path)
                else:
                    self._summary['unsupported_files'] += 1
                    self._fail()
            except ReportTreeSanitizerError:
                raise
            except Exception:
                self._fail()

    @staticmethod
    def _is_text_file(path):
        if file_is_binary(path):
            return False
        decoder = codecs.getincrementaldecoder('utf-8')()
        try:
            with open(path, 'rb') as source:
                while True:
                    chunk = source.read(64 * 1024)
                    if not chunk:
                        break
                    if b'\0' in chunk:
                        return False
                    decoder.decode(chunk, final=False)
            decoder.decode(b'', final=True)
            return True
        except (OSError, UnicodeError):
            return False

    def _copy_file(self, source, destination):
        if not self._is_text_file(source):
            self._summary['unsupported_files'] += 1
            self._fail()
        try:
            with open(source, 'rb') as source_stream, \
                    open(destination, 'wb') as destination_stream:
                sanitize_stream(source_stream, destination_stream,
                                session=self.session)
            shutil.copystat(source, destination, follow_symlinks=False)
            self._summary['files_processed'] += 1
            self._summary['text_files_sanitized'] += 1
        except Exception:
            self._fail()
