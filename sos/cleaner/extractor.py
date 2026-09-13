# This file is part of the sos project: https://github.com/sosreport/sos

"""Safe extraction of tar-based sosreport archives."""

import errno
import os
import posixpath
import re
import stat
import tarfile
import tempfile

from sos.cleaner.filesystem import remove_private_tree


class SafeReportExtractorError(Exception):
    """A fail-closed extraction error with counts-only state."""

    def __init__(self, summary):
        self.summary = dict(summary)
        super().__init__('safe report extraction failed')


class SafeReportExtractor:
    """Extract a supported tar archive into a private temporary tree."""

    # These are deliberately configurable for tests and future policy work.
    DEFAULT_MAX_MEMBERS = 100000
    DEFAULT_MAX_FILE_SIZE = 8 * 1024 * 1024 * 1024
    DEFAULT_MAX_TOTAL_SIZE = 32 * 1024 * 1024 * 1024

    def __init__(self, archive_path, temp_parent=None,
                 max_members=DEFAULT_MAX_MEMBERS,
                 max_file_size=DEFAULT_MAX_FILE_SIZE,
                 max_total_size=DEFAULT_MAX_TOTAL_SIZE):
        self.archive_path = os.path.abspath(archive_path)
        self.temp_parent = temp_parent
        self.max_members = max_members
        self.max_file_size = max_file_size
        self.max_total_size = max_total_size
        self._summary = {
            'members_seen': 0,
            'files_extracted': 0,
            'directories_created': 0,
            'symlinks_created': 0,
            'fifos_omitted': 0,
            'rejected_members': 0,
            'bytes_extracted': 0,
        }

    def summary(self):
        return dict(self._summary)

    def extract(self):
        staging = None
        archive_fd = None
        succeeded = False
        try:
            self._validate_limits()
            archive_fd = self._open_archive(self.archive_path)
            with os.fdopen(archive_fd, 'rb', closefd=True) as archive_stream:
                archive_fd = None
                with tarfile.open(fileobj=archive_stream, mode='r:*') as archive:
                    members = self._preflight(archive)
                    staging = tempfile.mkdtemp(
                        prefix='.sos-report-extract-', dir=self.temp_parent)
                    os.chmod(staging, 0o700)
                    self._extract_members(archive, members, staging)
            succeeded = True
            return staging
        except SafeReportExtractorError:
            raise
        except Exception:
            self._reject()
        finally:
            if archive_fd is not None:
                try:
                    os.close(archive_fd)
                except OSError:
                    pass
            if not succeeded and staging is not None and os.path.lexists(staging):
                try:
                    remove_private_tree(staging)
                except OSError:
                    pass

    def _validate_limits(self):
        if (not isinstance(self.max_members, int) or self.max_members < 1 or
                not isinstance(self.max_file_size, int) or
                self.max_file_size < 0 or
                not isinstance(self.max_total_size, int) or
                self.max_total_size < 0):
            self._reject()

    def _reject(self):
        self._summary['rejected_members'] += 1
        raise SafeReportExtractorError(self._summary)

    @staticmethod
    def _open_archive(path):
        if (not hasattr(os, 'O_NOFOLLOW') or os.open not in
                os.supports_dir_fd):
            raise OSError(errno.ENOTSUP, 'safe archive open unavailable')
        if os.path.islink(path):
            raise OSError(errno.ELOOP, 'archive link rejected')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW |
                     getattr(os, 'O_CLOEXEC', 0))
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError(errno.EINVAL, 'archive is not regular')
            return fd
        except Exception:
            os.close(fd)
            raise

    @staticmethod
    def _member_path(name):
        if not isinstance(name, str) or not name or '\x00' in name:
            raise ValueError
        if name.startswith('/'):
            raise ValueError
        # Archive paths use POSIX separators.  Preserve ordinary literal
        # backslashes, but reject forms that could become absolute or
        # traversing paths when consumed by Windows-oriented tooling.
        if (name.startswith('\\') or
                re.match(r'^[A-Za-z]:', name) or
                re.search(r'(?:^|/)\.\.?\\', name) or
                re.search(r'\\\.\.?(?:\\|/|$)', name)):
            raise ValueError
        # Tar paths are POSIX paths. Reject explicit parent components before
        # normalization so that alternate spellings cannot evade validation.
        parts = name.split('/')
        if any(part == '..' for part in parts):
            raise ValueError
        normalized = posixpath.normpath(name)
        if (normalized != name or normalized in ('', '.', '..') or
                normalized.startswith('../')):
            raise ValueError
        if posixpath.isabs(normalized):
            raise ValueError
        return normalized

    @staticmethod
    def _classify_member(member):
        if member.isdir():
            return 'directory'
        if member.isreg():
            return 'regular'
        if member.issym():
            return 'symlink'
        if member.islnk():
            return 'hardlink'
        if member.isfifo():
            return 'fifo'
        if member.ischr():
            return 'character'
        if member.isblk():
            return 'block'
        return 'unknown'

    @staticmethod
    def _symlink_target(path, target):
        """Return a safe archive-relative target, or raise ValueError."""
        if (not isinstance(target, str) or not target or '\x00' in target or
                target.startswith('\\') or '\\' in target or
                posixpath.isabs(target)):
            raise ValueError
        parent = posixpath.dirname(path)
        normalized = posixpath.normpath(posixpath.join(parent, target))
        if normalized in ('', '.', '..') or normalized.startswith('../'):
            raise ValueError
        return target

    def _preflight(self, archive):
        members = []
        paths = {}
        total = 0
        try:
            for member in archive:
                self._summary['members_seen'] += 1
                if self._summary['members_seen'] > self.max_members:
                    self._reject()
                kind = self._classify_member(member)
                path = self._member_path(member.name)
                if kind in ('symlink', 'fifo'):
                    if kind == 'symlink':
                        self._symlink_target(path, member.linkname)
                elif kind != 'regular' and kind != 'directory':
                    self._reject()
                if path in paths:
                    self._reject()
                if kind == 'regular':
                    if not isinstance(member.size, int) or member.size < 0:
                        self._reject()
                    if member.size > self.max_file_size:
                        self._reject()
                    total += member.size
                    if total > self.max_total_size:
                        self._reject()
                paths[path] = kind
                members.append((path, kind, member))
        except SafeReportExtractorError:
            raise
        except Exception:
            self._reject()

        for path, kind in paths.items():
            parts = path.split('/')
            for index in range(1, len(parts)):
                parent = '/'.join(parts[:index])
                if parent in paths and paths[parent] != 'directory':
                    self._reject()
        return sorted(members, key=lambda item: (item[0].count('/'), item[0]))

    @staticmethod
    def _safe_mode(mode, directory=False):
        # Never carry setuid, setgid, sticky, or special type bits from tar.
        allowed = 0o777
        return stat.S_IMODE(mode) & allowed

    def _root_fd(self, staging):
        if not hasattr(os, 'O_NOFOLLOW') or os.open not in os.supports_dir_fd:
            raise OSError(errno.ENOTSUP, 'safe extraction open unavailable')
        return os.open(staging, os.O_RDONLY | os.O_DIRECTORY |
                       os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0))

    def _ensure_directory(self, root_fd, relative):
        current = root_fd
        opened = []
        try:
            for component in relative.split('/') if relative else ():
                try:
                    child = os.open(component, os.O_RDONLY | os.O_DIRECTORY |
                                    os.O_NOFOLLOW, dir_fd=current)
                except FileNotFoundError:
                    os.mkdir(component, 0o700, dir_fd=current)
                    child = os.open(component, os.O_RDONLY | os.O_DIRECTORY |
                                    os.O_NOFOLLOW, dir_fd=current)
                    self._summary['directories_created'] += 1
                opened.append(child)
                current = child
            return current, opened
        except Exception:
            for fd in reversed(opened):
                os.close(fd)
            raise

    @staticmethod
    def _write_all(fd, data):
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError(errno.EIO, 'short extraction write')
            offset += written

    def _extract_members(self, archive, members, staging):
        root_fd = self._root_fd(staging)
        modes = {path: self._safe_mode(member.mode, kind == 'directory')
                 for path, kind, member in members}
        directory_modes = {path: modes[path] for path, kind, _ in members
                           if kind == 'directory'}
        symlink_members = [(path, member) for path, kind, member in members
                           if kind == 'symlink']
        try:
            for path, kind, member in members:
                if kind in ('symlink', 'fifo'):
                    if kind == 'fifo':
                        self._summary['fifos_omitted'] += 1
                    continue
                parent, _, basename = path.rpartition('/')
                parent_fd, opened = self._ensure_directory(root_fd, parent)
                try:
                    if kind == 'directory':
                        try:
                            os.mkdir(basename, 0o700, dir_fd=parent_fd)
                            self._summary['directories_created'] += 1
                        except FileExistsError:
                            existing = os.stat(basename, dir_fd=parent_fd,
                                               follow_symlinks=False)
                            if not stat.S_ISDIR(existing.st_mode):
                                self._reject()
                    else:
                        fd = os.open(basename, os.O_WRONLY | os.O_CREAT |
                                     os.O_EXCL | os.O_NOFOLLOW, 0o600,
                                     dir_fd=parent_fd)
                        try:
                            source = archive.extractfile(member)
                            if source is None:
                                self._reject()
                            with source:
                                remaining = member.size
                                while remaining:
                                    data = source.read(min(64 * 1024,
                                                           remaining))
                                    if not data:
                                        self._reject()
                                    self._write_all(fd, data)
                                    remaining -= len(data)
                                    self._summary['bytes_extracted'] += len(data)
                                if source.read(1):
                                    self._reject()
                            # Keep the private extracted tree readable by the
                            # invoking user.  Construction remains 0600; the
                            # final mode retains ordinary archive semantics
                            # while guaranteeing owner-read access.
                            os.fchmod(fd, modes[path] | stat.S_IRUSR)
                            self._summary['files_extracted'] += 1
                        finally:
                            os.close(fd)
                finally:
                    for child_fd in reversed(opened):
                        os.close(child_fd)
            # Create links only after all real files and directories exist.
            # Parent traversal remains no-follow and therefore cannot use a
            # previously-created link as an extraction directory.
            for path, member in symlink_members:
                parent, _, basename = path.rpartition('/')
                parent_fd, opened = self._ensure_directory(root_fd, parent)
                try:
                    os.symlink(member.linkname, basename, dir_fd=parent_fd)
                    self._summary['symlinks_created'] += 1
                finally:
                    for child_fd in reversed(opened):
                        os.close(child_fd)
            self._finalize_directory_modes(root_fd, directory_modes)
        finally:
            os.close(root_fd)

    def _finalize_directory_modes(self, root_fd, directory_modes):
        """Apply safe archive directory modes after construction."""
        for path, mode in sorted(directory_modes.items(),
                                  key=lambda item: item[0].count('/'),
                                  reverse=True):
                parent, _, basename = path.rpartition('/')
                parent_fd, opened = self._ensure_directory(root_fd, parent)
                try:
                    directory_fd = os.open(
                        basename, os.O_RDONLY | os.O_DIRECTORY |
                        os.O_NOFOLLOW, dir_fd=parent_fd)
                    try:
                        os.fchmod(directory_fd, mode)
                    finally:
                        os.close(directory_fd)
                finally:
                    for child_fd in reversed(opened):
                        os.close(child_fd)
