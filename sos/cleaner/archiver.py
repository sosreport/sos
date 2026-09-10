# This file is part of the sos project: https://github.com/sosreport/sos

"""Safe creation of a sanitized sosreport tar archive."""

import ctypes
import errno
import os
import posixpath
import shutil
import stat
import tarfile
import tempfile


class SafeReportArchiverError(Exception):
    """A fail-closed archive creation error with counts only."""

    def __init__(self, summary):
        self.summary = dict(summary)
        super().__init__('safe report archive creation failed')


class SafeReportArchiver:
    """Package an already validated tree into a canonical tar archive."""

    DEFAULT_MAX_MEMBERS = 100000
    DEFAULT_MAX_FILE_SIZE = 8 * 1024 * 1024 * 1024
    DEFAULT_MAX_TOTAL_SIZE = 32 * 1024 * 1024 * 1024

    def __init__(self, source, destination, output_format='xz',
                 max_members=DEFAULT_MAX_MEMBERS,
                 max_file_size=DEFAULT_MAX_FILE_SIZE,
                 max_total_size=DEFAULT_MAX_TOTAL_SIZE):
        self.source = os.path.abspath(source)
        self.destination = os.path.abspath(destination)
        self.output_format = output_format
        self.max_members = max_members
        self.max_file_size = max_file_size
        self.max_total_size = max_total_size
        self._summary = {
            'members_written': 0,
            'files_written': 0,
            'directories_written': 0,
            'symlinks_written': 0,
            'hardlinks_written': 0,
            'bytes_written': 0,
        }
        self._names = set()

    def summary(self):
        return dict(self._summary)

    def create(self):
        staging = None
        try:
            self._validate_inputs()
            parent = os.path.dirname(self.destination)
            staging_fd, staging = tempfile.mkstemp(
                prefix='.sos-report-archive-', suffix='.tmp', dir=parent)
            os.fchmod(staging_fd, 0o600)
            os.close(staging_fd)
            mode = 'w:xz'
            with tarfile.open(staging, mode=mode,
                              format=tarfile.USTAR_FORMAT) as archive:
                self._write_tree(archive)
            self._validate_archive(staging)
            self._publish_noreplace(staging)
            staging = None
            return self.destination
        except SafeReportArchiverError:
            raise
        except Exception:
            self._fail()
        finally:
            if staging is not None and os.path.lexists(staging):
                try:
                    os.unlink(staging)
                except OSError:
                    pass

    archive = create

    def _validate_inputs(self):
        if self.output_format != 'xz':
            self._fail()
        if not self.destination.endswith('.tar.xz'):
            self._fail()
        if (not isinstance(self.max_members, int) or self.max_members < 1 or
                not isinstance(self.max_file_size, int) or
                self.max_file_size < 0 or
                not isinstance(self.max_total_size, int) or
                self.max_total_size < 0):
            self._fail()
        if not os.path.isdir(self.source) or os.path.islink(self.source):
            self._fail()
        parent = os.path.dirname(self.destination)
        if not os.path.isdir(parent) or os.path.lexists(self.destination):
            self._fail()

    def _fail(self):
        raise SafeReportArchiverError(self._summary)

    @staticmethod
    def _member_name(relative):
        if (not relative or '\x00' in relative or relative.startswith('/')
                or relative.startswith('\\')):
            raise ValueError
        if any(part in ('', '.', '..') for part in relative.split('/')):
            raise ValueError
        normalized = posixpath.normpath(relative)
        if normalized != relative or normalized.startswith('../') or \
                posixpath.isabs(normalized):
            raise ValueError
        return normalized

    @staticmethod
    def _safe_mode(mode, directory=False):
        return stat.S_IMODE(mode) & (0o777 if directory else 0o666)

    @staticmethod
    def _classify_mode(mode):
        if stat.S_ISDIR(mode):
            return 'directory'
        if stat.S_ISREG(mode):
            return 'regular'
        if stat.S_ISLNK(mode):
            return 'symlink'
        return 'special'

    @staticmethod
    def _open_directory(name, parent_fd=None, observed=None):
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        if parent_fd is None:
            fd = os.open(name, flags)
        else:
            if os.open not in os.supports_dir_fd:
                raise OSError(errno.ENOTSUP, 'safe directory open unavailable')
            fd = os.open(name, flags, dir_fd=parent_fd)
        try:
            current = os.fstat(fd)
            if not stat.S_ISDIR(current.st_mode) or (observed is not None and
                    (current.st_dev, current.st_ino) !=
                    (observed.st_dev, observed.st_ino)):
                raise OSError(errno.EAGAIN, 'directory changed')
            return fd
        except Exception:
            os.close(fd)
            raise

    @staticmethod
    def _open_regular(name, parent_fd, observed):
        if (not hasattr(os, 'O_NOFOLLOW') or os.open not in
                os.supports_dir_fd):
            raise OSError(errno.ENOTSUP, 'safe file open unavailable')
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            current = os.fstat(fd)
            if (not stat.S_ISREG(current.st_mode) or
                    (current.st_dev, current.st_ino) !=
                    (observed.st_dev, observed.st_ino)):
                raise OSError(errno.EAGAIN, 'file changed')
            return fd, current
        except Exception:
            os.close(fd)
            raise

    def _tar_info(self, name, kind, mode, size=0, linkname=''):
        info = tarfile.TarInfo(name)
        info.uid = 0
        info.gid = 0
        info.uname = ''
        info.gname = ''
        info.mode = self._safe_mode(mode, kind == 'directory')
        info.mtime = 0
        info.pax_headers = {}
        if kind == 'directory':
            info.type = tarfile.DIRTYPE
        elif kind == 'symlink':
            info.type = tarfile.SYMTYPE
            info.linkname = linkname
        else:
            info.type = tarfile.REGTYPE
            info.size = size
        return info

    def _write_tree(self, archive):
        root_fd = self._open_directory(self.source)
        try:
            self._write_directory(archive, root_fd, '')
        finally:
            os.close(root_fd)

    def _write_directory(self, archive, source_fd, relative):
        try:
            entries = sorted(os.scandir(source_fd), key=lambda entry: entry.name)
        except Exception:
            self._fail()
        for entry in entries:
            observed = entry.stat(follow_symlinks=False)
            child = entry.name if not relative else relative + '/' + entry.name
            try:
                name = self._member_name(child)
                if name in self._names:
                    self._fail()
                self._names.add(name)
                kind = self._classify_mode(observed.st_mode)
                if kind == 'directory':
                    child_fd = self._open_directory(entry.name, source_fd,
                                                    observed)
                    try:
                        archive.addfile(self._tar_info(name, kind,
                                                       observed.st_mode))
                        self._summary['directories_written'] += 1
                        self._summary['members_written'] += 1
                        self._write_directory(archive, child_fd, name)
                    finally:
                        os.close(child_fd)
                elif kind == 'regular':
                    if observed.st_size > self.max_file_size:
                        self._fail()
                    if self._summary['bytes_written'] + observed.st_size > \
                            self.max_total_size:
                        self._fail()
                    fd, opened = self._open_regular(entry.name, source_fd,
                                                    observed)
                    try:
                        info = self._tar_info(name, kind, opened.st_mode,
                                              opened.st_size)
                        with os.fdopen(fd, 'rb', closefd=True) as stream:
                            archive.addfile(info, stream)
                        fd = None
                        self._summary['files_written'] += 1
                        self._summary['bytes_written'] += opened.st_size
                        self._summary['members_written'] += 1
                    finally:
                        if fd is not None:
                            os.close(fd)
                elif kind == 'symlink':
                    target = os.readlink(entry.name, dir_fd=source_fd)
                    self._validate_link_target(target, relative)
                    archive.addfile(self._tar_info(name, kind,
                                                   observed.st_mode, 0,
                                                   target))
                    self._summary['symlinks_written'] += 1
                    self._summary['members_written'] += 1
                else:
                    self._fail()
                if self._summary['members_written'] > self.max_members:
                    self._fail()
            except SafeReportArchiverError:
                raise
            except Exception:
                self._fail()

    @staticmethod
    def _validate_link_target(target, relative=''):
        if (not target or target.startswith('/') or target.startswith('\\') or
                '\\' in target):
            raise ValueError
        normalized = posixpath.normpath(posixpath.join(relative, target))
        if normalized in ('', '..') or normalized.startswith('../'):
            raise ValueError

    @staticmethod
    def _validate_archive_name(name):
        if (not name or name.startswith('/') or name.startswith('\\') or
                any(part in ('', '.', '..') for part in name.split('/')) or
                posixpath.normpath(name) != name):
            raise ValueError

    def _validate_archive(self, path):
        names = set()
        members = 0
        total = 0
        try:
            with tarfile.open(path, mode='r:xz') as archive:
                for member in archive:
                    members += 1
                    if members > self.max_members:
                        self._fail()
                    self._validate_archive_name(member.name)
                    if member.name in names:
                        self._fail()
                    names.add(member.name)
                    if member.uid != 0 or member.gid != 0 or member.uname or \
                            member.gname or member.mtime != 0 or \
                            member.pax_headers:
                        self._fail()
                    if member.isdir():
                        continue
                    if member.isreg():
                        if member.size < 0 or member.size > self.max_file_size:
                            self._fail()
                        total += member.size
                        if total > self.max_total_size:
                            self._fail()
                    elif member.issym():
                        parent, _, _ = member.name.rpartition('/')
                        self._validate_link_target(member.linkname, parent)
                    else:
                        self._fail()
                if members != self._summary['members_written'] or \
                        total != self._summary['bytes_written']:
                    self._fail()
        except SafeReportArchiverError:
            raise
        except Exception:
            self._fail()

    def _publish_noreplace(self, staging):
        if os.name != 'posix':
            raise OSError(errno.ENOTSUP, 'atomic no-replace unavailable')
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            renameat2 = libc.renameat2
        except (AttributeError, OSError):
            raise OSError(errno.ENOTSUP,
                          'atomic no-replace unavailable') from None
        renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p,
                              ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        renameat2.restype = ctypes.c_int
        if renameat2(-100, os.fsencode(staging), -100,
                     os.fsencode(self.destination), 1) != 0:
            error = ctypes.get_errno()
            raise OSError(error, 'atomic no-replace publication failed')
