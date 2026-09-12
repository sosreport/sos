# This file is part of the sos project: https://github.com/sosreport/sos

"""Independent residual privacy validation for completed report archives."""

import errno
import os
import posixpath
import socket
import stat
import tarfile

from sos.cleaner.archiver import SafeReportArchiver
from sos.cleaner.report_residual import (build_manifest_patterns,
                                         known_original_residual)
from sos.cleaner.text_residual import _has_residual, _packed


class ReportArchiveResidualError(Exception):
    """A generic archive privacy failure with counts-only state."""

    def __init__(self, summary):
        self.summary = dict(summary)
        super().__init__('report archive residual validation failed')


class ReportArchiveResidualValidator:
    """Validate a private tar.xz artifact independently of its source tree."""

    DEFAULT_MAX_MEMBERS = 100000
    DEFAULT_MAX_FILE_SIZE = 8 * 1024 * 1024 * 1024
    DEFAULT_MAX_TOTAL_SIZE = 32 * 1024 * 1024 * 1024

    def __init__(self, archive_path, manifest,
                 max_members=DEFAULT_MAX_MEMBERS,
                 max_file_size=DEFAULT_MAX_FILE_SIZE,
                 max_total_size=DEFAULT_MAX_TOTAL_SIZE):
        self.archive_path = os.path.abspath(archive_path)
        self.manifest = manifest
        self.max_members = max_members
        self.max_file_size = max_file_size
        self.max_total_size = max_total_size
        self._summary = {
            'members_checked': 0,
            'regular_files_checked': 0,
            'directories_checked': 0,
            'symlinks_checked': 0,
            'bytes_checked': 0,
        }
        raw = manifest.raw_mappings()
        self._patterns = build_manifest_patterns(raw)
        self._ipv4_aliases = {
            _packed(alias, socket.AF_INET)
            for original, alias in raw['ipv4'].items() if original != alias
        }
        self._ipv6_aliases = {
            _packed(alias, socket.AF_INET6)
            for original, alias in raw['ipv6'].items() if original != alias
        }

    def summary(self):
        return dict(self._summary)

    def _fail(self):
        raise ReportArchiveResidualError(self._summary)

    @staticmethod
    def _validate_name(name):
        if (not name or '\x00' in name or name.startswith('/') or
                name.startswith('\\') or
                any(part in ('', '.', '..') for part in name.split('/')) or
                posixpath.normpath(name) != name):
            raise ValueError

    @staticmethod
    def _validate_link_target(target, member_name):
        parent, _, _ = member_name.rpartition('/')
        SafeReportArchiver._validate_link_target(target, parent)

    def _check_text(self, text):
        if known_original_residual(text, self._patterns):
            self._fail()
        if _has_residual(text, self._ipv4_aliases, self._ipv6_aliases):
            self._fail()

    def _check_member_metadata(self, member):
        if (member.uid != 0 or member.gid != 0 or member.uname != '' or
                member.gname != '' or member.mtime != 0 or
                member.pax_headers or member.mode != stat.S_IMODE(member.mode) or
                member.mode & 0o7000 or
                (member.isreg() and not member.mode & stat.S_IRUSR)):
            self._fail()

    def _check_regular(self, archive, member):
        if member.size < 0 or member.size > self.max_file_size:
            self._fail()
        if self._summary['bytes_checked'] + member.size > self.max_total_size:
            self._fail()
        stream = archive.extractfile(member)
        if stream is None:
            self._fail()
        read = 0
        try:
            for raw_line in stream:
                read += len(raw_line)
                if read > member.size or b'\0' in raw_line:
                    self._fail()
                self._check_text(raw_line.decode('utf-8'))
            if read != member.size:
                self._fail()
        except ReportArchiveResidualError:
            raise
        except (OSError, UnicodeError, tarfile.TarError):
            self._fail()
        finally:
            stream.close()
        self._summary['bytes_checked'] += read
        self._summary['regular_files_checked'] += 1

    def validate(self):
        if (not isinstance(self.max_members, int) or self.max_members < 1 or
                not isinstance(self.max_file_size, int) or
                self.max_file_size < 0 or
                not isinstance(self.max_total_size, int) or
                self.max_total_size < 0):
            self._fail()
        try:
            if not hasattr(os, 'O_NOFOLLOW'):
                raise OSError(errno.ENOTSUP, 'safe archive open unavailable')
            fd = os.open(self.archive_path,
                         os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0))
            try:
                observed = os.fstat(fd)
                if not stat.S_ISREG(observed.st_mode):
                    self._fail()
                with os.fdopen(fd, 'rb', closefd=True) as stream:
                    fd = None
                    with tarfile.open(fileobj=stream, mode='r:xz') as archive:
                        names = set()
                        kinds = {}
                        for member in archive:
                            self._summary['members_checked'] += 1
                            if self._summary['members_checked'] > self.max_members:
                                self._fail()
                            self._validate_name(member.name)
                            if member.name in names:
                                self._fail()
                            names.add(member.name)
                            known_original_residual(member.name, self._patterns) and self._fail()
                            self._check_member_metadata(member)
                            if member.isdir():
                                kinds[member.name] = 'directory'
                                self._summary['directories_checked'] += 1
                            elif member.isreg():
                                kinds[member.name] = 'regular'
                                self._check_regular(archive, member)
                            elif member.issym():
                                self._validate_link_target(member.linkname,
                                                           member.name)
                                self._check_text(member.linkname)
                                kinds[member.name] = 'symlink'
                                self._summary['symlinks_checked'] += 1
                            else:
                                self._fail()
                        for name in names:
                            parts = name.split('/')[:-1]
                            for index in range(1, len(parts) + 1):
                                parent = '/'.join(parts[:index])
                                if parent in kinds and kinds[parent] != 'directory':
                                    self._fail()
                current = os.stat(self.archive_path, follow_symlinks=False)
                if ((current.st_dev, current.st_ino) !=
                        (observed.st_dev, observed.st_ino)):
                    self._fail()
            finally:
                if fd is not None:
                    os.close(fd)
        except ReportArchiveResidualError:
            raise
        except Exception:
            self._fail()
        return self.summary()
