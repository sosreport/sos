# This file is part of the sos project: https://github.com/sosreport/sos

"""Independent residual privacy validation for completed report archives."""

import errno
import io
import os
import posixpath
import socket
import stat
import tarfile

from sos.cleaner.archiver import SafeReportArchiver
from sos.cleaner.report_residual import (ResidualMatcher,
                                         known_original_residual)
from sos.cleaner.text_residual import _has_residual, _packed
from sos.cleaner.pacemaker import (PacemakerSchedulerInput,
                                   PacemakerSchedulerInputError)
from sos.cleaner.edid import DrmEdidPolicy
from sos.cleaner.corosync import (CorosyncLog, CorosyncLogError,
                                   PacemakerLog)
from sos.cleaner.sssd import SssdLog
from sos.cleaner.acpi import is_path as is_acpi_path
from sos.cleaner.systemd import is_path as is_systemd_coredump_path
from sos.cleaner.selinux_store import (active_store_module_path,
                                       active_store_path)
from sos.cleaner.selinux_cil import DirectCil, DirectCilError


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
    _corosync_authkey_path = 'etc/corosync/authkey'
    _selinux_file_contexts_bin_paths = frozenset((
        'etc/selinux/targeted/contexts/files/file_contexts.bin',
        'etc/selinux/targeted/contexts/files/file_contexts.homedirs.bin',
    ))
    _selinux_binary_policy_versions = frozenset(
        str(version) for version in range(15, 36))
    _process_environment_max_pid = 4194303
    _timezone_paths = frozenset((
        'usr/share/zoneinfo/Etc/UTC',
        'usr/share/zoneinfo/Australia/Sydney',
    ))

    @classmethod
    def _is_corosync_authkey_path(cls, name):
        parts = tuple(name.split('/'))
        target = tuple(cls._corosync_authkey_path.split('/'))
        return parts == target or (len(parts) == 4 and parts[1:] == target)

    @classmethod
    def _is_selinux_file_contexts_bin_path(cls, name):
        parts = tuple(name.split('/'))
        return name in cls._selinux_file_contexts_bin_paths or any(
            len(parts) == len(target.split('/')) + 1 and
            parts[1:] == tuple(target.split('/'))
            for target in cls._selinux_file_contexts_bin_paths)

    @classmethod
    def _is_selinux_binary_policy_path(cls, name):
        parts = tuple(name.split('/'))
        for candidate in (parts, parts[1:] if parts else ()):
            if (candidate[:4] == ('etc', 'selinux', 'targeted', 'policy') and
                    len(candidate) == 5 and
                    candidate[4].startswith('policy.') and
                    candidate[4][7:] in cls._selinux_binary_policy_versions):
                return True
        return False

    @classmethod
    def _is_process_environment_path(cls, name):
        parts = tuple(name.split('/'))
        for candidate in (parts, parts[1:] if parts else ()):
            if len(candidate) != 3 or candidate[0] != 'proc':
                continue
            pid, filename = candidate[1:]
            if (not pid or not pid.isascii() or not pid.isdecimal() or
                    pid[0] == '0' or filename != 'environ'):
                return False
            return 1 <= int(pid) <= cls._process_environment_max_pid
        return False

    @classmethod
    def _is_selinux_active_store_omission_path(cls, name):
        relative = tuple(name.split('/'))
        return ((active_store_module_path(relative) is not None and
                 not DirectCil.is_path(relative)) or
                any(active_store_path(relative, filename) for filename in (
                    'policy.kern', 'policy.linked', 'modules_checksum',
                    'commit_num')))

    @classmethod
    def _is_timezone_path(cls, name):
        parts = tuple(name.split('/'))
        return name in cls._timezone_paths or (
            len(parts) == 4 and '/'.join(parts[1:]) in cls._timezone_paths)

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
        self._patterns = ResidualMatcher(raw)
        self._ipv4_aliases = {
            _packed(alias, socket.AF_INET)
            for original, alias in raw['ipv4'].items() if original != alias
        }
        self._ipv6_aliases = {
            _packed(alias, socket.AF_INET6)
            for original, alias in raw['ipv6'].items() if original != alias
        }
        self._corosync_members = 0
        self._corosync_bytes = 0

    def summary(self):
        return dict(self._summary)

    def _fail(self):
        raise ReportArchiveResidualError(self._summary)

    def _accept_corosync_payload(self, size):
        if self._corosync_members >= CorosyncLog.MAX_MEMBERS or \
                self._corosync_bytes + size > CorosyncLog.MAX_AGGREGATE:
            self._fail()
        self._corosync_members += 1
        self._corosync_bytes += size

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
                not SafeReportArchiver._safe_pax_headers(member) or
                member.mode != stat.S_IMODE(member.mode) or
                member.mode & 0o7000 or
                (member.isreg() and not member.mode & stat.S_IRUSR)):
            self._fail()

    def _check_regular(self, archive, member):
        if member.size < 0 or member.size > self.max_file_size:
            self._fail()
        if self._summary['bytes_checked'] + member.size > self.max_total_size:
            self._fail()
        is_corosync = CorosyncLog.is_path(tuple(member.name.split('/')))
        is_pacemaker = PacemakerLog.is_path(tuple(member.name.split('/')))
        if DirectCil.is_path(tuple(member.name.split('/'))):
            if member.size > DirectCil.MAX_COMPRESSED:
                self._fail()
            stream = archive.extractfile(member)
            if stream is None:
                self._fail()
            try:
                payload = DirectCil.decode(stream, member.size)
                DirectCil.residual_check(payload, self._check_text)
            except (OSError, UnicodeError, DirectCilError, tarfile.TarError):
                self._fail()
            finally:
                stream.close()
            self._summary['bytes_checked'] += member.size
            self._summary['regular_files_checked'] += 1
            return
        if ((is_corosync or is_pacemaker) and
                member.size > CorosyncLog.MAX_COMPRESSED):
            self._fail()
        stream = archive.extractfile(member)
        if stream is None:
            self._fail()
        if PacemakerSchedulerInput.is_path(member.name):
            try:
                payload = PacemakerSchedulerInput.decode(stream, member.size)
                PacemakerSchedulerInput.residual_check(payload)
                for raw_line in payload.splitlines(keepends=True):
                    self._check_text(raw_line.decode('utf-8'))
            except ReportArchiveResidualError:
                raise
            except (OSError, UnicodeError, PacemakerSchedulerInputError):
                self._fail()
            finally:
                stream.close()
            self._summary['bytes_checked'] += member.size
            self._summary['regular_files_checked'] += 1
            return
        if is_corosync:
            try:
                compressed = stream.read(member.size)
                payload = CorosyncLog.decode(io.BytesIO(compressed),
                                             member.size)
                self._accept_corosync_payload(len(payload))
                for raw_line in payload.decode('utf-8').splitlines(
                        keepends=True):
                    self._check_text(raw_line)
            except ReportArchiveResidualError:
                raise
            except (OSError, UnicodeError, CorosyncLogError, tarfile.TarError):
                self._fail()
            finally:
                stream.close()
            if len(compressed) != member.size:
                self._fail()
            self._summary['bytes_checked'] += member.size
            self._summary['regular_files_checked'] += 1
            return
        if is_pacemaker:
            try:
                compressed = stream.read(member.size)
                payload = PacemakerLog.decode(io.BytesIO(compressed),
                                              member.size)
                for raw_line in payload.decode('utf-8').splitlines(
                        keepends=True):
                    self._check_text(raw_line)
            except ReportArchiveResidualError:
                raise
            except (OSError, UnicodeError, CorosyncLogError, tarfile.TarError):
                self._fail()
            finally:
                stream.close()
            if len(compressed) != member.size:
                self._fail()
            self._summary['bytes_checked'] += member.size
            self._summary['regular_files_checked'] += 1
            return
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
                            if DirectCil.is_path(tuple(member.name.split('/'))):
                                if not member.isreg():
                                    self._fail()
                            if (self._is_corosync_authkey_path(member.name) or
                                    self._is_selinux_file_contexts_bin_path(
                                        member.name) or
                                    self._is_selinux_binary_policy_path(
                                        member.name) or
                                    self._is_selinux_active_store_omission_path(
                                        member.name) or
                                    self._is_process_environment_path(
                                        member.name) or
                                    is_acpi_path(tuple(member.name.split('/'))) or
                                    is_systemd_coredump_path(
                                        tuple(member.name.split('/'))) or
                                    self._is_timezone_path(member.name) or
                                    SssdLog.is_path(
                                        tuple(member.name.split('/'))) or
                                    DrmEdidPolicy.is_path(
                                        tuple(member.name.split('/')))):
                                self._fail()
                            if (CorosyncLog.is_path(
                                    tuple(member.name.split('/'))) and
                                    not member.isreg()):
                                self._fail()
                            if (PacemakerLog.is_path(
                                    tuple(member.name.split('/'))) and
                                    not member.isreg()):
                                self._fail()
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
