# This file is part of the sos project: https://github.com/sosreport/sos

"""Sanitization of an already-extracted report directory."""

import codecs
import ctypes
import bz2
import errno
import os
import posixpath
import re
import socket
import stat
import sys
import tempfile

from sos.cleaner.text import sanitize_stream
from sos.cleaner.report_residual import (
    ResidualMatcher, ReportTreeResidualValidator, known_original_residual)
from sos.cleaner.filesystem import remove_private_tree
from sos.cleaner.openpgp import is_public_keyring_fd
from sos.cleaner.tzif import is_tzif_fd
from sos.cleaner.symlink import validate_symlink_target
from sos.cleaner.pacemaker import PacemakerSchedulerInput
from sos.cleaner.edid import DrmEdidPolicy
from sos.cleaner.corosync import (CorosyncLog, CorosyncLogError,
                                   PacemakerLog)
from sos.cleaner.sssd import SssdLog
from sos.cleaner.acpi import (is_path as is_acpi_path,
                              classify_fd as classify_acpi_fd)
from sos.cleaner.systemd import (is_path as is_systemd_coredump_path,
                                 classify_fd as classify_systemd_coredump_fd)
from sos.cleaner.selinux_store import (active_store_module_path,
                                       active_store_path)
from sos.cleaner.selinux_cil import DirectCil, DirectCilError
from sos.cleaner.text_residual import _has_residual, _packed


class ReportTreeSanitizerError(Exception):
    """A safe tree-sanitization failure carrying counts only."""

    def __init__(self, summary):
        self.summary = dict(summary)
        super().__init__('report tree sanitization failed')


class ReportTreeSanitizer:
    """Build a sanitized destination tree using one shared session."""

    _optional_report_root = r'(?:[^/]+/)?'
    _sysstat_binary = re.compile(
        _optional_report_root + r'var/log/(?:sa|sysstat)/sa\d+$')
    _proc_pci_binary = re.compile(
        _optional_report_root +
        r'proc/bus/pci/[0-9a-fA-F]{2}/[0-9a-fA-F]{2}\.[0-7]$')
    _proc_lockd_binary = re.compile(
        _optional_report_root + r'proc/fs/lockd/nlm_end_grace$')
    _proc_rt_acct_binary = re.compile(
        _optional_report_root + r'proc/[1-9]\d*/net/rt_acct$')
    _process_environment_max_size = 8 * 1024 * 1024
    _process_environment_max_pid = 4194303
    _apt_eipp_binary = re.compile(
        _optional_report_root + r'var/log/apt/eipp\.log\.xz$')
    _apt_keyring_binary = re.compile(
        _optional_report_root + r'etc/apt/trusted\.gpg$|' +
        _optional_report_root + r'etc/apt/trusted\.gpg\.d/[^/]+\.gpg$')
    _timezone_binary = re.compile(
        _optional_report_root +
        r'usr/share/zoneinfo/(?:Etc/UTC|Australia/Sydney)$')
    _sysstat_magic = (b'\x96\xd5\x75\x21', b'\x21\x75\xd5\x96')
    _xz_magic = b'\xfd7zXZ\x00'
    _corosync_authkey_path = ('etc', 'corosync', 'authkey')
    _corosync_authkey_min_size = 128
    _corosync_authkey_max_size = 4096
    _selinux_file_contexts_bin_paths = frozenset((
        ('etc', 'selinux', 'targeted', 'contexts', 'files',
         'file_contexts.bin'),
        ('etc', 'selinux', 'targeted', 'contexts', 'files',
         'file_contexts.homedirs.bin'),
    ))
    _selinux_file_contexts_bin_max_size = 8 * 1024 * 1024
    _selinux_binary_policy_min_version = 15
    _selinux_binary_policy_max_version = 35
    _selinux_binary_policy_max_size = 64 * 1024 * 1024
    _selinux_policy_magic = 0xf97cff8c
    _selinux_policy_target = b'SE Linux'
    _selinux_policy_header_size = 32
    _selinux_module_compressed_max_size = 16 * 1024 * 1024
    _selinux_module_decompressed_max_size = 64 * 1024 * 1024
    _selinux_module_ratio = 200

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
            'symlinks_preserved': 0,
            'hardlinks_preserved': 0,
            'special_files_rejected': 0,
            'binary_files_omitted': 0,
            'sysstat_files_omitted': 0,
            'proc_sys_files_omitted': 0,
            'compressed_files_omitted': 0,
            'package_keyrings_omitted': 0,
            'timezone_files_omitted': 0,
            'cluster_authkeys_omitted': 0,
            'selinux_binary_contexts_omitted': 0,
            'selinux_binary_policies_omitted': 0,
            'selinux_module_hll_payloads_omitted': 0,
            'selinux_module_cil_caches_omitted': 0,
            'selinux_linked_policies_omitted': 0,
            'selinux_policy_store_metadata_omitted': 0,
            'selinux_module_language_metadata_omitted': 0,
            'selinux_direct_cil_sanitized': 0,
            'process_environments_omitted': 0,
            'pacemaker_scheduler_inputs_sanitized': 0,
            'display_edids_omitted': 0,
            'corosync_logs_sanitized': 0,
            'pacemaker_logs_sanitized': 0,
            'sssd_logs_omitted': 0,
            'acpi_tables_omitted': 0,
            'systemd_coredump_helpers_omitted': 0,
        }
        self._hardlinks = {}
        self._staging_root = None
        self._corosync_members = 0
        self._corosync_bytes = 0
        self._pacemaker_members = 0
        self._pacemaker_bytes = 0
        self._corosync_residual_patterns = None
        self._corosync_ipv4_aliases = set()
        self._corosync_ipv6_aliases = set()
        self._pacemaker_members = 0
        self._pacemaker_bytes = 0

    def sanitize(self):
        """Publish a complete sanitized tree or raise without publishing."""
        self._validate_roots()
        parent = os.path.dirname(self.destination)
        if not os.path.isdir(parent):
            self._fail()
        if os.path.lexists(self.destination):
            self._fail()
        self._stabilize_mappings()
        mapping_snapshot = self.session.mapping_manifest().raw_mappings()
        self.session.freeze_mappings()
        self._prepare_corosync_residual_check()
        self._corosync_members = 0
        self._corosync_bytes = 0
        staging = tempfile.mkdtemp(prefix='.sos-report-sanitize-', dir=parent)
        self._staging_root = staging
        try:
            self._summary['directories_created'] += 1
            source_fd = self._open_directory(self.source, None, None)
            source_stat = os.fstat(source_fd)
            try:
                self._copy_directory(source_fd, staging, ())
            finally:
                os.close(source_fd)
            staging_fd = self._open_directory(staging, None, None)
            try:
                self._copy_stat(source_stat, destination_fd=staging_fd)
            finally:
                os.close(staging_fd)
            if (self.session.mapping_manifest().raw_mappings() !=
                    mapping_snapshot):
                self._fail()
            ReportTreeResidualValidator(
                staging, self.session.mapping_manifest()).validate()
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
                remove_private_tree(staging)

    def _stabilize_mappings(self):
        """Discover content identities before creating sanitized paths."""
        source_fd = self._open_directory(self.source, None, None)
        try:
            with open(os.devnull, 'wb') as sink:
                self._stabilize_directory(source_fd, sink, ())
        finally:
            os.close(source_fd)

    def _stabilize_directory(self, source_fd, sink, relative):
        try:
            entries = sorted(os.scandir(source_fd), key=lambda entry: entry.name)
        except Exception:
            self._fail()
        for entry in entries:
            try:
                observed = entry.stat(follow_symlinks=False)
                object_type = self._classify_mode(observed.st_mode)
                candidate = relative + (entry.name,)
                if DrmEdidPolicy.is_path(candidate) and \
                        object_type != 'regular':
                    self._summary['unsupported_files'] += 1
                    self._fail()
                if CorosyncLog.is_path(candidate) and \
                        object_type != 'regular':
                    self._summary['unsupported_files'] += 1
                    self._fail()
                if (PacemakerLog.is_path(candidate) or
                        SssdLog.is_path(candidate) or
                        is_acpi_path(candidate) or
                        is_systemd_coredump_path(candidate)) and \
                        object_type != 'regular':
                    self._summary['unsupported_files'] += 1
                    self._fail()
                if active_store_module_path(candidate) is not None and \
                        object_type != 'regular':
                    self._summary['unsupported_files'] += 1
                    self._fail()
                if object_type == 'directory':
                    child_fd = self._open_directory(entry.name, source_fd,
                                                    observed)
                    try:
                        self._stabilize_directory(
                            child_fd, sink, relative + (entry.name,))
                    finally:
                        os.close(child_fd)
                elif object_type == 'regular':
                    self._stabilize_file(
                        entry.name, source_fd, observed, sink,
                        relative + (entry.name,))
                elif object_type == 'symlink':
                    if (self._is_process_environment_path(candidate) or
                            DrmEdidPolicy.is_path(candidate)):
                        self._summary['unsupported_files'] += 1
                        self._fail()
                    if candidate == self._corosync_authkey_path or (
                            len(candidate) == 4 and
                            candidate[1:] == self._corosync_authkey_path):
                        self._summary['unsupported_files'] += 1
                        self._fail()
                    if self._is_selinux_file_contexts_bin_path(candidate):
                        self._summary['unsupported_files'] += 1
                        self._fail()
                    if (active_store_module_path(candidate) is not None or
                            self._is_selinux_active_store_path(candidate)):
                        self._summary['unsupported_files'] += 1
                        self._fail()
                    # Identity discovery never interprets link targets.
                    continue
                else:
                    self._summary['unsupported_files'] += 1
                    self._summary['special_files_rejected'] += 1
                    self._fail()
            except ReportTreeSanitizerError:
                raise
            except Exception:
                self._fail()

    def _stabilize_file(self, name, source_fd, observed, sink, relative):
        fd, opened = self._open_regular(
            name, source_fd, observed,
            require_single_link=CorosyncLog.is_path(relative))
        selinux_store = self._selinux_store_policy(
            relative, opened, fd, source_fd)
        if selinux_store == 'reject':
            os.close(fd)
            self._summary['unsupported_files'] += 1
            self._fail()
        if selinux_store is not None:
            if selinux_store == 'selinux_direct_cil':
                try:
                    with os.fdopen(fd, 'rb', closefd=True) as stream:
                        payload = DirectCil.decode(stream, opened.st_size)
                    DirectCil.transform(payload, self.session)
                except Exception:
                    self._summary['unsupported_files'] += 1
                    self._fail()
                return
            os.close(fd)
            self._omit_binary(selinux_store, count=False)
            return
        if PacemakerSchedulerInput.is_path(relative):
            try:
                PacemakerSchedulerInput.sanitize(
                    os.fdopen(fd, 'rb', closefd=True), opened.st_size,
                    self.session, sink)
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                self._fail()
            return
        if CorosyncLog.is_path(relative):
            try:
                with os.fdopen(fd, 'rb', closefd=True) as source_stream:
                    CorosyncLog.sanitize(
                        source_stream, opened.st_size, self.session, sink,
                        on_decoded=self._accept_corosync_payload)
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                self._fail()
            return
        if PacemakerLog.is_path(relative):
            try:
                with os.fdopen(fd, 'rb', closefd=True) as source_stream:
                    PacemakerLog.sanitize(
                        source_stream, opened.st_size, self.session, sink,
                        on_decoded=self._accept_pacemaker_payload)
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                self._fail()
            return
        if SssdLog.is_path(relative):
            try:
                with os.fdopen(fd, 'rb', closefd=True) as source_stream:
                    result = SssdLog.classify(source_stream, opened.st_size)
            except Exception:
                result = 'reject'
            if result == 'omit':
                self._omit_binary('sssd_log', count=False)
                return
            self._summary['unsupported_files'] += 1
            self._fail()
        if is_acpi_path(relative):
            result = classify_acpi_fd(fd, opened, relative)
            os.close(fd)
            if result == 'omit':
                self._omit_binary('acpi_table', count=False)
                return
            self._summary['unsupported_files'] += 1
            self._fail()
        if is_systemd_coredump_path(relative):
            result = classify_systemd_coredump_fd(fd, opened)
            os.close(fd)
            if result == 'omit':
                self._omit_binary('systemd_coredump_helper', count=False)
                return
            self._summary['unsupported_files'] += 1
            self._fail()
        if self._timezone_binary.fullmatch('/'.join(relative)):
            if opened.st_nlink != 1 or not is_tzif_fd(fd):
                os.close(fd)
                self._summary['unsupported_files'] += 1
                self._fail()
            os.close(fd)
            self._omit_binary('timezone', count=False)
            return
        if DrmEdidPolicy.is_path(relative):
            result = DrmEdidPolicy.classify_fd(fd, opened)
            os.close(fd)
            if result == 'omit':
                self._omit_binary('display_edid', count=False)
                return
            self._summary['unsupported_files'] += 1
            self._fail()
        process_environment = self._process_environment_policy(
            relative, opened)
        if process_environment == 'reject':
            os.close(fd)
            self._summary['unsupported_files'] += 1
            self._fail()
        if process_environment == 'omit':
            os.close(fd)
            return
        selinux_policy = self._selinux_binary_policy(relative, opened, fd)
        if selinux_policy == 'reject':
            os.close(fd)
            self._summary['unsupported_files'] += 1
            self._fail()
        if selinux_policy == 'omit':
            os.close(fd)
            return
        selinux_policy = self._selinux_file_contexts_bin_policy(relative, opened)
        if selinux_policy == 'reject':
            os.close(fd)
            self._summary['unsupported_files'] += 1
            self._fail()
        if selinux_policy == 'omit':
            os.close(fd)
            return
        authkey_policy = self._corosync_authkey_policy(relative, opened)
        if authkey_policy == 'reject':
            os.close(fd)
            self._summary['unsupported_files'] += 1
            self._fail()
        if authkey_policy == 'omit':
            os.close(fd)
            return
        if not self._is_text_fd(fd):
            category = self._binary_omission_class(
                relative, fd)
            os.close(fd)
            if category is not None:
                return
            self._summary['unsupported_files'] += 1
            self._fail()
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            with os.fdopen(fd, 'rb', closefd=True) as source_stream:
                sanitize_stream(
                    source_stream, sink, session=self.session,
                    redactor=self.session.new_stream_redactor())
        except Exception:
            self._fail()

    def summary(self):
        """Return counts only for the current operation."""
        return dict(self._summary)

    def _fail(self, cause=None):
        self._summary['failures'] += 1
        if cause is None:
            cause = sys.exc_info()[1]
        error = ReportTreeSanitizerError(self._summary)
        if cause is None:
            raise error
        raise error from cause

    def _accept_corosync_payload(self, size):
        if self._corosync_members >= CorosyncLog.MAX_MEMBERS or \
                self._corosync_bytes + size > CorosyncLog.MAX_AGGREGATE:
            raise OSError(errno.EFBIG, 'Corosync log budget exceeded')
        self._corosync_members += 1
        self._corosync_bytes += size

    def _accept_pacemaker_payload(self, size):
        if self._pacemaker_members >= PacemakerLog.MAX_MEMBERS or \
                self._pacemaker_bytes + size > PacemakerLog.MAX_AGGREGATE:
            raise OSError(errno.EFBIG, 'Pacemaker log budget exceeded')
        self._pacemaker_members += 1
        self._pacemaker_bytes += size

    def _prepare_corosync_residual_check(self):
        raw = self.session.mapping_manifest().raw_mappings()
        self._corosync_residual_patterns = ResidualMatcher(raw)
        self._corosync_ipv4_aliases = {
            _packed(alias, socket.AF_INET)
            for original, alias in raw['ipv4'].items()
            if original != alias
        }
        self._corosync_ipv6_aliases = {
            _packed(alias, socket.AF_INET6)
            for original, alias in raw['ipv6'].items()
            if original != alias
        }

    def _check_direct_cil_residual(self, payload):
        raw = self.session.mapping_manifest().raw_mappings()
        matcher = ResidualMatcher(raw)
        ipv4 = {_packed(alias, socket.AF_INET)
                for original, alias in raw['ipv4'].items()
                if original != alias}
        ipv6 = {_packed(alias, socket.AF_INET6)
                for original, alias in raw['ipv6'].items()
                if original != alias}
        def check(text):
            if (known_original_residual(text, matcher) or
                    _has_residual(text, ipv4, ipv6)):
                raise DirectCilError('CIL residual privacy')
        DirectCil.residual_check(payload, check)

    def _check_corosync_output_residual(self, payload, relative_path=None):
        try:
            text = payload.decode('utf-8')
        except UnicodeError:
            raise CorosyncLogError('non-UTF-8 residual') from None
        for line in text.splitlines(keepends=True):
            category = self._corosync_residual_patterns.match_category(line)
            if category is not None:
                raise CorosyncLogError(
                    'residual privacy', 'known ' + category.rstrip('s'),
                    relative_path)
            if _has_residual(line, self._corosync_ipv4_aliases,
                             self._corosync_ipv6_aliases):
                raise CorosyncLogError(
                    'residual privacy', 'generic residual', relative_path)

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

    @staticmethod
    def _nofollow_flags(directory=False):
        required = ('O_NOFOLLOW',)
        if any(not hasattr(os, name) for name in required):
            raise OSError(errno.ENOTSUP, 'no-follow open unavailable')
        flags = os.O_RDONLY | os.O_NOFOLLOW
        if directory:
            if not hasattr(os, 'O_DIRECTORY'):
                raise OSError(errno.ENOTSUP, 'directory open unavailable')
            flags |= os.O_DIRECTORY
        if hasattr(os, 'O_CLOEXEC'):
            flags |= os.O_CLOEXEC
        return flags

    def _open_directory(self, path, parent_fd, observed):
        flags = self._nofollow_flags(directory=True)
        if parent_fd is None:
            fd = os.open(path, flags)
        else:
            if os.open not in os.supports_dir_fd:
                raise OSError(errno.ENOTSUP, 'directory-relative open unavailable')
            fd = os.open(path, flags, dir_fd=parent_fd)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISDIR(opened.st_mode):
                raise OSError(errno.ELOOP, 'directory type changed')
            if observed is not None and (opened.st_dev != observed.st_dev or
                                          opened.st_ino != observed.st_ino):
                raise OSError(errno.EAGAIN, 'directory changed during open')
            return fd
        except Exception:
            os.close(fd)
            raise

    def _open_regular(self, name, parent_fd, observed,
                      require_single_link=False):
        if os.open not in os.supports_dir_fd:
            raise OSError(errno.ENOTSUP, 'directory-relative open unavailable')
        fd = os.open(name, self._nofollow_flags(), dir_fd=parent_fd)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode):
                raise OSError(errno.ELOOP, 'regular-file type changed')
            if opened.st_dev != observed.st_dev or opened.st_ino != observed.st_ino:
                raise OSError(errno.EAGAIN, 'regular file changed during open')
            if require_single_link and opened.st_nlink != 1:
                raise OSError(errno.EMLINK, 'hard-linked Corosync log')
            return fd, opened
        except Exception:
            os.close(fd)
            raise

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

    def _sanitized_relative(self, relative):
        parts = [] if relative in ('', '.') else relative.split('/')
        return '/'.join(self._sanitized_name(part) if part not in ('', '.', '..')
                        else part for part in parts)

    def _rewrite_symlink_target(self, target, relative_dir, name):
        source_member = '/'.join(relative_dir + (name,))
        try:
            validate_symlink_target(source_member, target)
        except ValueError:
            self._summary['unsupported_files'] += 1
            self._fail()
        if not target or posixpath.isabs(target):
            self._summary['unsupported_files'] += 1
            self._fail()
        source_parent = '/'.join(relative_dir)
        source_target = posixpath.normpath(
            posixpath.join(source_parent, target))
        if source_target == '..' or source_target.startswith('../'):
            self._summary['unsupported_files'] += 1
            self._fail()
        destination_parent = self._sanitized_relative(source_parent)
        destination_target = self._sanitized_relative(source_target)
        rewritten = posixpath.relpath(destination_target or '.',
                                      destination_parent or '.')
        rewritten_target = posixpath.normpath(
            posixpath.join(destination_parent, rewritten))
        if rewritten_target == '..' or rewritten_target.startswith('../'):
            self._summary['unsupported_files'] += 1
            self._fail()
        destination_member = '/'.join(
            part for part in (destination_parent, name) if part)
        try:
            validate_symlink_target(destination_member, rewritten)
        except ValueError:
            self._summary['unsupported_files'] += 1
            self._fail()
        return rewritten

    def _copy_symlink(self, name, source_fd, destination, relative_dir):
        if os.readlink not in os.supports_dir_fd:
            raise OSError(errno.ENOTSUP, 'directory-relative symlink read unavailable')
        target = os.readlink(name, dir_fd=source_fd)
        rewritten = self._rewrite_symlink_target(
            target, relative_dir[:-1], name)
        os.symlink(rewritten, destination)
        self._summary['symlinks_preserved'] += 1

    @staticmethod
    def _copy_stat(source_stat, destination_fd=None):
        if destination_fd is None or not callable(getattr(os, 'fchmod', None)):
            raise OSError(errno.ENOTSUP, 'fd-based metadata unavailable')
        os.fchmod(destination_fd, stat.S_IMODE(source_stat.st_mode))
        os.utime(destination_fd, ns=(source_stat.st_atime_ns,
                                     source_stat.st_mtime_ns))

    def _copy_directory(self, source_fd, destination, relative_dir):
        try:
            entries = sorted(os.scandir(source_fd), key=lambda entry: entry.name)
        except Exception:
            self._fail()
        seen = set()
        for entry in entries:
            name = self._sanitized_name(entry.name)
            if name in seen or os.path.lexists(os.path.join(destination, name)):
                self._fail()
            seen.add(name)
            destination_path = os.path.join(destination, name)
            try:
                observed = entry.stat(follow_symlinks=False)
                child_relative = relative_dir + (entry.name,)
                object_type = self._classify_mode(observed.st_mode)
                if DrmEdidPolicy.is_path(child_relative) and \
                        object_type != 'regular':
                    self._summary['unsupported_files'] += 1
                    self._fail()
                if CorosyncLog.is_path(child_relative) and \
                        object_type != 'regular':
                    self._summary['unsupported_files'] += 1
                    self._fail()
                if object_type == 'symlink':
                    if (self._is_process_environment_path(child_relative) or
                            DrmEdidPolicy.is_path(child_relative)):
                        self._summary['unsupported_files'] += 1
                        self._fail()
                    if child_relative == self._corosync_authkey_path or (
                            len(child_relative) == 4 and
                            child_relative[1:] == self._corosync_authkey_path):
                        self._summary['unsupported_files'] += 1
                        self._fail()
                    if self._is_selinux_file_contexts_bin_path(child_relative):
                        self._summary['unsupported_files'] += 1
                        self._fail()
                    if DirectCil.is_path(child_relative):
                        self._summary['unsupported_files'] += 1
                        self._fail()
                    self._copy_symlink(name=entry.name, source_fd=source_fd,
                                       destination=destination_path,
                                       relative_dir=child_relative)
                elif object_type == 'directory':
                    child_fd = self._open_directory(entry.name, source_fd,
                                                    observed)
                    os.mkdir(destination_path)
                    self._summary['directories_created'] += 1
                    try:
                        self._copy_directory(child_fd, destination_path,
                                             child_relative)
                    finally:
                        os.close(child_fd)
                    destination_fd = self._open_directory(
                        destination_path, None, None)
                    try:
                        self._copy_stat(observed, destination_fd=destination_fd)
                    finally:
                        os.close(destination_fd)
                elif object_type == 'regular':
                    self._copy_file(entry.name, source_fd, observed,
                                    destination_path, child_relative)
                else:
                    self._summary['special_files_rejected'] += 1
                    self._summary['unsupported_files'] += 1
                    self._fail()
            except ReportTreeSanitizerError:
                raise
            except Exception:
                self._fail()

    @staticmethod
    def _classify_mode(mode):
        if stat.S_ISLNK(mode):
            return 'symlink'
        if stat.S_ISDIR(mode):
            return 'directory'
        if stat.S_ISREG(mode):
            return 'regular'
        return 'special'

    @staticmethod
    def _is_text_fd(fd):
        decoder = codecs.getincrementaldecoder('utf-8')()
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            while True:
                chunk = os.read(fd, 64 * 1024)
                if not chunk:
                    break
                if b'\0' in chunk:
                    return False
                decoder.decode(chunk, final=False)
            decoder.decode(b'', final=True)
            return True
        except (OSError, UnicodeError):
            return False

    def _binary_omission_class(self, relative, fd):
        path = '/'.join(relative)
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            prefix = os.read(fd, 16)
            os.lseek(fd, 0, os.SEEK_SET)
        except OSError:
            return None
        if self._sysstat_binary.fullmatch(path) and \
                prefix.startswith(self._sysstat_magic):
            return 'sysstat'
        if (self._proc_pci_binary.fullmatch(path) or
                self._proc_lockd_binary.fullmatch(path) or
                self._proc_rt_acct_binary.fullmatch(path)):
            return 'proc_sys'
        if self._apt_eipp_binary.fullmatch(path) and \
                prefix.startswith(self._xz_magic):
            return 'compressed'
        if self._apt_keyring_binary.fullmatch(path) and \
                is_public_keyring_fd(fd):
            return 'package_keyrings'
        if self._timezone_binary.fullmatch(path) and is_tzif_fd(fd):
            return 'timezone'
        return None

    @classmethod
    def _is_selinux_file_contexts_bin_path(cls, relative):
        relative = tuple(relative)
        return relative in cls._selinux_file_contexts_bin_paths or any(
            len(relative) == len(target) + 1 and relative[1:] == target
            for target in cls._selinux_file_contexts_bin_paths)

    @classmethod
    def _process_environment_pid(cls, relative):
        relative = tuple(relative)
        if len(relative) == 3 and relative[0] == 'proc':
            parts = relative
        elif len(relative) == 4 and relative[1] == 'proc':
            parts = relative[1:]
        else:
            return None
        pid, filename = parts[1:]
        if (not pid or not pid.isascii() or not pid.isdecimal() or
                pid[0] == '0' or filename != 'environ'):
            return None
        value = int(pid)
        if not (1 <= value <= cls._process_environment_max_pid):
            return None
        return value

    @classmethod
    def _is_process_environment_path(cls, relative):
        return cls._process_environment_pid(relative) is not None

    @classmethod
    def _process_environment_policy(cls, relative, observed):
        if not cls._is_process_environment_path(relative):
            return None
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            return 'reject'
        if observed.st_size > cls._process_environment_max_size:
            return 'reject'
        return 'omit'

    @classmethod
    def _selinux_file_contexts_bin_policy(cls, relative, observed):
        if not cls._is_selinux_file_contexts_bin_path(relative):
            return None
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            return 'reject'
        if not (0 < observed.st_size <=
                cls._selinux_file_contexts_bin_max_size):
            return 'reject'
        return 'omit'

    @classmethod
    def _selinux_binary_policy_name(cls, relative):
        relative = tuple(relative)
        target = ('etc', 'selinux', 'targeted', 'policy')
        if relative[:len(target)] == target:
            remainder = relative[len(target):]
        elif (len(relative) > len(target) and
              relative[1:1 + len(target)] == target):
            remainder = relative[1 + len(target):]
        else:
            return None
        if len(remainder) != 1:
            return None
        name = remainder[0]
        if not name.startswith('policy.'):
            return None
        version_text = name[len('policy.'):]
        if (not version_text or not version_text.isascii() or
                not version_text.isdecimal() or version_text[0] == '0'):
            return False
        version = int(version_text)
        if not (cls._selinux_binary_policy_min_version <= version <=
                cls._selinux_binary_policy_max_version):
            return False
        return version

    @classmethod
    def _selinux_binary_policy(cls, relative, observed, fd):
        version = cls._selinux_binary_policy_name(relative)
        if version is None:
            return None
        if version is False:
            return 'reject'
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            return 'reject'
        if not (0 < observed.st_size <= cls._selinux_binary_policy_max_size):
            return 'reject'
        try:
            header = os.pread(fd, cls._selinux_policy_header_size, 0)
        except (AttributeError, OSError):
            return 'reject'
        if len(header) != cls._selinux_policy_header_size:
            return 'reject'
        import struct
        magic, identifier_length = struct.unpack('<2I', header[:8])
        if magic != cls._selinux_policy_magic or identifier_length != len(
                cls._selinux_policy_target):
            return 'reject'
        if header[8:8 + identifier_length] != cls._selinux_policy_target:
            return 'reject'
        embedded_version, _config, symbol_count, ocon_count = struct.unpack(
            '<4I', header[16:])
        if (embedded_version != version or symbol_count != 8 or
                not (1 <= ocon_count <= 16)):
            return 'reject'
        return 'omit'

    @classmethod
    def _is_selinux_active_store_path(cls, relative):
        return any(active_store_path(relative, name) for name in (
            'policy.kern', 'policy.linked', 'modules_checksum', 'commit_num'))

    @staticmethod
    def _selinux_store_sibling(parent_fd, name):
        try:
            fd = os.open(name, ReportTreeSanitizer._nofollow_flags(),
                         dir_fd=parent_fd)
            observed = os.fstat(fd)
            if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
                os.close(fd)
                return None
            return fd, observed
        except OSError:
            return None

    @classmethod
    def _selinux_bzip_valid(cls, fd, compressed_size):
        """Validate one bounded store-compression stream without publishing it."""
        if not (0 < compressed_size <= cls._selinux_module_compressed_max_size):
            return False
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            decoder = bz2.BZ2Decompressor()
            produced = 0
            remaining = compressed_size
            first = True
            while remaining:
                chunk = os.read(fd, min(64 * 1024, remaining))
                if not chunk:
                    return False
                remaining -= len(chunk)
                if first:
                    first = False
                    if (len(chunk) < 4 or chunk[:3] != b'BZh' or
                            chunk[3:4] not in b'123456789'):
                        return False
                produced += len(decoder.decompress(chunk))
                if produced > cls._selinux_module_decompressed_max_size:
                    return False
                if decoder.eof and (decoder.unused_data or remaining):
                    return False
            return decoder.eof and produced <= max(
                1 * 1024 * 1024,
                compressed_size * cls._selinux_module_ratio)
        except (OSError, EOFError, ValueError, bz2.BZ2DecompressorError):
            return False

    @classmethod
    def _selinux_module_policy(cls, relative, observed, fd, parent_fd):
        leaf = active_store_module_path(relative)
        if leaf is None:
            return None
        if (leaf is False or not stat.S_ISREG(observed.st_mode) or
                observed.st_nlink != 1 or
                not (0 < observed.st_size <=
                     cls._selinux_module_compressed_max_size)):
            return 'reject'
        if leaf == 'lang_ext':
            if observed.st_size not in (2, 3):
                return 'reject'
            try:
                value = os.pread(fd, observed.st_size, 0)
            except (AttributeError, OSError):
                return 'reject'
            return ('selinux_module_language_metadata'
                    if value in (b'pp', b'cil') else 'reject')
        siblings = {}
        try:
            for name in ('hll', 'cil', 'lang_ext'):
                sibling = cls._selinux_store_sibling(parent_fd, name)
                if sibling is not None:
                    siblings[name] = sibling
            if 'lang_ext' not in siblings:
                return 'reject'
            ext_fd, _ext_stat = siblings['lang_ext']
            try:
                extension = os.read(ext_fd, 4)
            finally:
                os.close(ext_fd)
            if extension == b'cil' and 'hll' not in siblings and leaf == 'cil':
                try:
                    with os.fdopen(os.dup(fd), 'rb', closefd=True) as stream:
                        payload = DirectCil.decode(stream, observed.st_size)
                    DirectCil._lex(payload)
                except Exception:
                    return 'reject'
                # The duplicate shares the open-file description and its
                # decompression read advances the original offset.  The
                # caller must still be able to consume the source payload.
                os.lseek(fd, 0, os.SEEK_SET)
                return 'selinux_direct_cil'
            if extension != b'pp' or ('hll' not in siblings or
                                       'cil' not in siblings):
                return 'reject'
            if not cls._selinux_bzip_valid(fd, observed.st_size):
                return 'reject'
            return ('selinux_module_hll_payload' if leaf == 'hll' else
                    'selinux_module_cil_cache')
        finally:
            for name, (sibling_fd, _sibling_stat) in siblings.items():
                if name != 'lang_ext':
                    os.close(sibling_fd)

    @classmethod
    def _selinux_store_policy(cls, relative, observed, fd, parent_fd):
        module = cls._selinux_module_policy(relative, observed, fd, parent_fd)
        if module is not None:
            return module
        if not cls._is_selinux_active_store_path(relative):
            return None
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            return 'reject'
        name = tuple(relative)[-1]
        if name in ('policy.kern', 'policy.linked'):
            if not (0 < observed.st_size <=
                    cls._selinux_binary_policy_max_size):
                return 'reject'
            try:
                header = os.pread(fd, cls._selinux_policy_header_size, 0)
            except (AttributeError, OSError):
                return 'reject'
            if len(header) != cls._selinux_policy_header_size:
                return 'reject'
            import struct
            magic, identifier_length = struct.unpack('<2I', header[:8])
            if (magic != cls._selinux_policy_magic or
                    identifier_length != len(cls._selinux_policy_target) or
                    header[8:16] != cls._selinux_policy_target):
                return 'reject'
            version, _config, symbol_count, ocon_count = struct.unpack(
                '<4I', header[16:])
            if not (cls._selinux_binary_policy_min_version <= version <=
                    cls._selinux_binary_policy_max_version and
                    symbol_count == 8 and 1 <= ocon_count <= 16):
                return 'reject'
            return ('selinux_binary_policy' if name == 'policy.kern' else
                    'selinux_linked_policy')
        if name == 'modules_checksum':
            if observed.st_size != 72:
                return 'reject'
            try:
                value = os.pread(fd, 72, 0)
            except (AttributeError, OSError):
                return 'reject'
            if not re.fullmatch(rb'sha256:[0-9a-f]{64}\0', value):
                return 'reject'
            return 'selinux_policy_store_metadata'
        if name == 'commit_num':
            if observed.st_size != 32:
                return 'reject'
            try:
                value = os.pread(fd, 32, 0)
            except (AttributeError, OSError):
                return 'reject'
            import struct
            serial, = struct.unpack('<I', value[:4])
            return ('selinux_policy_store_metadata'
                    if serial > 0 and value[4:] == b'\0' * 28 else
                    'reject')
        return None

    @classmethod
    def _corosync_authkey_policy(cls, relative, observed):
        """Classify only the default Corosync credential path."""
        relative = tuple(relative)
        if relative != cls._corosync_authkey_path and not (
                len(relative) == 4 and
                relative[1:] == cls._corosync_authkey_path):
            return None
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            return 'reject'
        if not (cls._corosync_authkey_min_size <= observed.st_size <=
                cls._corosync_authkey_max_size):
            return 'reject'
        return 'omit'

    def _omit_binary(self, category, count=True):
        if not count:
            return
        self._summary['binary_files_omitted'] += 1
        category_key = {
            'package_keyrings': 'package_keyrings_omitted',
            'timezone': 'timezone_files_omitted',
            'cluster_authkey': 'cluster_authkeys_omitted',
            'selinux_file_contexts_bin': 'selinux_binary_contexts_omitted',
            'selinux_binary_policy': 'selinux_binary_policies_omitted',
            'selinux_module_hll_payload':
                'selinux_module_hll_payloads_omitted',
            'selinux_module_cil_cache':
                'selinux_module_cil_caches_omitted',
            'selinux_linked_policy': 'selinux_linked_policies_omitted',
            'selinux_policy_store_metadata':
                'selinux_policy_store_metadata_omitted',
            'selinux_module_language_metadata':
                'selinux_module_language_metadata_omitted',
            'process_environment': 'process_environments_omitted',
            'display_edid': 'display_edids_omitted',
            'sssd_log': 'sssd_logs_omitted',
            'acpi_table': 'acpi_tables_omitted',
            'systemd_coredump_helper':
                'systemd_coredump_helpers_omitted',
        }.get(category, f'{category}_files_omitted')
        self._summary[category_key] += 1
        self._summary['files_processed'] += 1

    def _copy_file(self, name, source_fd, observed, destination, relative):
        fd, opened = self._open_regular(
            name, source_fd, observed,
            require_single_link=CorosyncLog.is_path(relative))
        selinux_store = self._selinux_store_policy(
            relative, opened, fd, source_fd)
        if selinux_store == 'reject':
            os.close(fd)
            self._summary['unsupported_files'] += 1
            self._fail()
        if selinux_store is not None:
            if selinux_store == 'selinux_direct_cil':
                output_fd = None
                try:
                    with os.fdopen(fd, 'rb', closefd=True) as source_stream:
                        payload = DirectCil.decode(source_stream,
                                                   opened.st_size)
                    sanitized = DirectCil.transform(payload, self.session)
                    self._check_direct_cil_residual(sanitized)
                    output_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                    if hasattr(os, 'O_NOFOLLOW'):
                        output_flags |= os.O_NOFOLLOW
                    output_fd = os.open(destination, output_flags, 0o600)
                    with os.fdopen(output_fd, 'wb', closefd=False) as output:
                        output.write(DirectCil.encode(sanitized))
                    self._copy_stat(opened, destination_fd=output_fd)
                    os.close(output_fd)
                    output_fd = None
                    self._summary['files_processed'] += 1
                    self._summary['selinux_direct_cil_sanitized'] += 1
                    return
                except Exception:
                    if output_fd is not None:
                        os.close(output_fd)
                    self._fail()
            os.close(fd)
            self._omit_binary(selinux_store)
            return
        if PacemakerSchedulerInput.is_path(relative):
            output_fd = None
            try:
                output_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                if hasattr(os, 'O_NOFOLLOW'):
                    output_flags |= os.O_NOFOLLOW
                output_fd = os.open(destination, output_flags, 0o600)
                with os.fdopen(fd, 'rb', closefd=True) as source_stream, \
                        os.fdopen(output_fd, 'wb', closefd=False) as plain_output:
                    sanitized = PacemakerSchedulerInput.sanitize(
                        source_stream, opened.st_size, self.session)
                    compressed = PacemakerSchedulerInput.encode(sanitized)
                    plain_output.write(compressed)
                self._copy_stat(opened, destination_fd=output_fd)
                os.close(output_fd)
                output_fd = None
                self._summary['files_processed'] += 1
                self._summary[
                    'pacemaker_scheduler_inputs_sanitized'] += 1
                return
            except Exception:
                if output_fd is not None:
                    os.close(output_fd)
                self._fail()
        if CorosyncLog.is_path(relative):
            output_fd = None
            try:
                output_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                if hasattr(os, 'O_NOFOLLOW'):
                    output_flags |= os.O_NOFOLLOW
                output_fd = os.open(destination, output_flags, 0o600)
                with os.fdopen(fd, 'rb', closefd=True) as source_stream, \
                        os.fdopen(output_fd, 'wb', closefd=False) as output:
                    sanitized = CorosyncLog.sanitize(
                        source_stream, opened.st_size, self.session,
                        on_decoded=self._accept_corosync_payload,
                        residual_check=lambda payload: self
                        ._check_corosync_output_residual(
                            payload, relative))
                    output.write(CorosyncLog.encode(sanitized))
                self._copy_stat(opened, destination_fd=output_fd)
                os.close(output_fd)
                output_fd = None
                self._summary['files_processed'] += 1
                self._summary['corosync_logs_sanitized'] += 1
                return
            except Exception:
                if output_fd is not None:
                    os.close(output_fd)
                self._fail()
        if PacemakerLog.is_path(relative):
            output_fd = None
            try:
                output_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                if hasattr(os, 'O_NOFOLLOW'):
                    output_flags |= os.O_NOFOLLOW
                output_fd = os.open(destination, output_flags, 0o600)
                with os.fdopen(fd, 'rb', closefd=True) as source_stream, \
                        os.fdopen(output_fd, 'wb', closefd=False) as output:
                    sanitized = PacemakerLog.sanitize(
                        source_stream, opened.st_size, self.session,
                        on_decoded=self._accept_pacemaker_payload,
                        residual_check=lambda payload: self
                        ._check_corosync_output_residual(
                            payload, relative))
                    output.write(PacemakerLog.encode(sanitized))
                self._copy_stat(opened, destination_fd=output_fd)
                os.close(output_fd)
                output_fd = None
                self._summary['files_processed'] += 1
                self._summary['pacemaker_logs_sanitized'] += 1
                return
            except Exception:
                if output_fd is not None:
                    os.close(output_fd)
                self._fail()
        if SssdLog.is_path(relative):
            try:
                with os.fdopen(fd, 'rb', closefd=True) as source_stream:
                    result = SssdLog.classify(source_stream, opened.st_size)
            except Exception:
                result = 'reject'
            if result == 'omit':
                self._omit_binary('sssd_log')
                return
            self._summary['unsupported_files'] += 1
            self._fail()
        if is_acpi_path(relative):
            result = classify_acpi_fd(fd, opened, relative)
            os.close(fd)
            if result == 'omit':
                self._omit_binary('acpi_table')
                return
            self._summary['unsupported_files'] += 1
            self._fail()
        if is_systemd_coredump_path(relative):
            result = classify_systemd_coredump_fd(fd, opened)
            os.close(fd)
            if result == 'omit':
                self._omit_binary('systemd_coredump_helper')
                return
            self._summary['unsupported_files'] += 1
            self._fail()
        if self._timezone_binary.fullmatch('/'.join(relative)):
            if opened.st_nlink != 1 or not is_tzif_fd(fd):
                os.close(fd)
                self._summary['unsupported_files'] += 1
                self._fail()
            os.close(fd)
            self._omit_binary('timezone')
            return
        if DrmEdidPolicy.is_path(relative):
            result = DrmEdidPolicy.classify_fd(fd, opened)
            os.close(fd)
            if result == 'omit':
                self._omit_binary('display_edid')
                return
            self._summary['unsupported_files'] += 1
            self._fail()
        process_environment = self._process_environment_policy(
            relative, opened)
        if process_environment == 'reject':
            os.close(fd)
            self._summary['unsupported_files'] += 1
            self._fail()
        if process_environment == 'omit':
            os.close(fd)
            self._omit_binary('process_environment')
            return
        selinux_policy = self._selinux_binary_policy(relative, opened, fd)
        if selinux_policy == 'reject':
            os.close(fd)
            self._summary['unsupported_files'] += 1
            self._fail()
        if selinux_policy == 'omit':
            os.close(fd)
            self._omit_binary('selinux_binary_policy')
            return
        selinux_policy = self._selinux_file_contexts_bin_policy(relative, opened)
        if selinux_policy == 'reject':
            os.close(fd)
            self._summary['unsupported_files'] += 1
            self._fail()
        if selinux_policy == 'omit':
            os.close(fd)
            self._omit_binary('selinux_file_contexts_bin')
            return
        authkey_policy = self._corosync_authkey_policy(relative, opened)
        if authkey_policy == 'reject':
            os.close(fd)
            self._summary['unsupported_files'] += 1
            self._fail()
        if authkey_policy == 'omit':
            os.close(fd)
            self._omit_binary('cluster_authkey')
            return
        key = (opened.st_dev, opened.st_ino)
        existing = self._hardlinks.get(key)
        if existing is not None:
            try:
                existing_stat = os.lstat(existing)
                root = os.path.commonpath((self._staging_root, existing))
                if root != self._staging_root or not stat.S_ISREG(
                        existing_stat.st_mode):
                    raise OSError(errno.ELOOP, 'invalid staged hard-link target')
                os.close(fd)
                os.link(existing, destination, follow_symlinks=False)
                linked = os.stat(destination, follow_symlinks=False)
                if (linked.st_dev, linked.st_ino) != key and \
                        (linked.st_dev, linked.st_ino) != (
                            existing_stat.st_dev, existing_stat.st_ino):
                    raise OSError(errno.EIO, 'hard-link validation failed')
                self._summary['hardlinks_preserved'] += 1
                self._summary['files_processed'] += 1
                return
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                self._fail()
        if not self._is_text_fd(fd):
            category = self._binary_omission_class(relative, fd)
            os.close(fd)
            if category is not None:
                self._omit_binary(category)
                return
            self._summary['unsupported_files'] += 1
            self._fail()
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            file_redactor = self.session.new_stream_redactor()
            output_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, 'O_NOFOLLOW'):
                output_flags |= os.O_NOFOLLOW
            if hasattr(os, 'O_CLOEXEC'):
                output_flags |= os.O_CLOEXEC
            output_fd = None
            output_fd = os.open(destination, output_flags, 0o600)
            with os.fdopen(fd, 'rb', closefd=True) as source_stream, \
                    os.fdopen(output_fd, 'wb', closefd=False) as destination_stream:
                sanitize_stream(source_stream, destination_stream,
                                session=self.session,
                                redactor=file_redactor)
            self._copy_stat(opened, destination_fd=output_fd)
            os.close(output_fd)
            output_fd = None
            self._hardlinks[key] = destination
            self._summary['files_processed'] += 1
            self._summary['text_files_sanitized'] += 1
        except Exception:
            self._fail()
