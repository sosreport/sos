# This file is part of the sos project: https://github.com/sosreport/sos

"""Sanitization of an already-extracted report directory."""

import codecs
import ctypes
import errno
import os
import posixpath
import re
import stat
import tempfile

from sos.cleaner.text import sanitize_stream
from sos.cleaner.report_residual import ReportTreeResidualValidator
from sos.cleaner.filesystem import remove_private_tree
from sos.cleaner.openpgp import is_public_keyring_fd
from sos.cleaner.tzif import is_tzif_fd


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
    _apt_eipp_binary = re.compile(
        _optional_report_root + r'var/log/apt/eipp\.log\.xz$')
    _apt_keyring_binary = re.compile(
        _optional_report_root + r'etc/apt/trusted\.gpg$|' +
        _optional_report_root + r'etc/apt/trusted\.gpg\.d/[^/]+\.gpg$')
    _timezone_binary = re.compile(
        _optional_report_root + r'usr/share/zoneinfo/Etc/UTC$')
    _sysstat_magic = (b'\x96\xd5\x75\x21', b'\x21\x75\xd5\x96')
    _xz_magic = b'\xfd7zXZ\x00'

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
        }
        self._hardlinks = {}
        self._staging_root = None

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
            self._copy_stat(source_stat, staging)
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
        fd, _opened = self._open_regular(name, source_fd, observed)
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

    def _open_regular(self, name, parent_fd, observed):
        if os.open not in os.supports_dir_fd:
            raise OSError(errno.ENOTSUP, 'directory-relative open unavailable')
        fd = os.open(name, self._nofollow_flags(), dir_fd=parent_fd)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode):
                raise OSError(errno.ELOOP, 'regular-file type changed')
            if opened.st_dev != observed.st_dev or opened.st_ino != observed.st_ino:
                raise OSError(errno.EAGAIN, 'regular file changed during open')
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

    def _rewrite_symlink_target(self, target, relative_dir):
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
        return rewritten

    def _copy_symlink(self, name, source_fd, destination, relative_dir):
        if os.readlink not in os.supports_dir_fd:
            raise OSError(errno.ENOTSUP, 'directory-relative symlink read unavailable')
        target = os.readlink(name, dir_fd=source_fd)
        rewritten = self._rewrite_symlink_target(target, relative_dir[:-1])
        os.symlink(rewritten, destination)
        self._summary['symlinks_preserved'] += 1

    @staticmethod
    def _copy_stat(source_stat, destination):
        os.chmod(destination, stat.S_IMODE(source_stat.st_mode),
                 follow_symlinks=False)
        os.utime(destination, ns=(source_stat.st_atime_ns,
                                  source_stat.st_mtime_ns),
                 follow_symlinks=False)

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
                if object_type == 'symlink':
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
                    self._copy_stat(observed, destination_path)
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

    def _omit_binary(self, category):
        self._summary['binary_files_omitted'] += 1
        category_key = {
            'package_keyrings': 'package_keyrings_omitted',
            'timezone': 'timezone_files_omitted',
        }.get(category, f'{category}_files_omitted')
        self._summary[category_key] += 1
        self._summary['files_processed'] += 1

    def _copy_file(self, name, source_fd, observed, destination, relative):
        fd, opened = self._open_regular(name, source_fd, observed)
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
            try:
                output_fd = os.open(destination, output_flags, 0o600)
                with os.fdopen(fd, 'rb', closefd=True) as source_stream, \
                        os.fdopen(output_fd, 'wb', closefd=True) as destination_stream:
                    output_fd = None
                    sanitize_stream(source_stream, destination_stream,
                                    session=self.session,
                                    redactor=file_redactor)
            finally:
                if output_fd is not None:
                    os.close(output_fd)
            self._copy_stat(opened, destination)
            self._hardlinks[key] = destination
            self._summary['files_processed'] += 1
            self._summary['text_files_sanitized'] += 1
        except Exception:
            self._fail()
