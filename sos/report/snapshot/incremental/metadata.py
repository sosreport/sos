# Copyright (C) 2026 Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import fnmatch
import hashlib
import logging
import os
import stat
from functools import lru_cache

try:
    import grp
    import pwd
except ImportError:
    grp = None
    pwd = None

try:
    import selinux
    selinux_enabled = selinux.is_selinux_enabled()
except ImportError:
    selinux = None
    selinux_enabled = False

log = logging.getLogger('sos')

# Only files under these paths are content-hashed today.  Files
# elsewhere are compared on stat metadata alone, so content changes
# that preserve size/mtime/ctime/mode/owner are not detected there.
# This is change-tracking, not an integrity/IDS mechanism.
#
# TODO: extend the hashing coverage in the future to other paths
# and command outputs. We could maybe even add a configurable
# option so users can specify directories.
HASH_CRITICAL_PATHS = (
    '/etc/',
    '/boot/',
    '/usr/bin/',
    '/usr/sbin/',
    '/lib/systemd/'
)
HASH_SIZE_LIMIT = 10 * 1024 * 1024

# TODO: Lets skip this in the first implementation,
# but investigate how to addsome of these filesystem
# types without causing slowness or hangs.
SKIP_FS_TYPES = {
    'proc', 'sysfs', 'tmpfs', 'devtmpfs', 'devpts', 'debugfs',
    'tracefs', 'cgroup', 'cgroup2', 'pstore', 'bpf', 'configfs',
    'securityfs', 'fusectl', 'hugetlbfs', 'mqueue', 'ramfs',
    'nfs', 'nfs4', 'cifs', 'smbfs', 'autofs', 'fuse.sshfs',
    'ncpfs', 'afs', 'glusterfs', 'lustre'
}

_FILE_TYPE_MAP = {
    stat.S_ISREG: "file",
    stat.S_ISDIR: "directory",
    stat.S_ISBLK: "block_device",
    stat.S_ISCHR: "char_device",
    stat.S_ISFIFO: "fifo",
    stat.S_ISLNK: "symlink",
    stat.S_ISSOCK: "socket",
}


@lru_cache(maxsize=1)
def _get_mounts():
    """Parse /proc/mounts and return a sorted list of
    (mount_point, fs_type).

    The result is memoized forthe process. We will use
    ``_invalidate_mounts_cache()`` to force a re-read,
    for example when running tests or after a
    long-running collection).
    """
    try:
        with open('/proc/mounts', 'r', encoding='UTF-8') as f:
            mounts = []
            for line in f:
                parts = line.split()
                if len(parts) >= 3:
                    mounts.append((parts[1], parts[2]))
            mounts.sort(key=lambda mount: len(mount[0]), reverse=True)
            return mounts
    except OSError:
        return []


def _invalidate_mounts_cache():
    """Reset the cached mount table so the next call re-reads
    /proc/mounts."""
    _get_mounts.cache_clear()


def _get_filesystem_type(path):
    """Get the filesystem type for a given path by parsing
    /proc/mounts.

    Return the filesystem type (e.g., 'ext4', 'nfs', 'proc',
    'sysfs') or None if the filesystem type cannot be determined.

    :param path: The filesystem path to check
    :type path: str

    :returns: Filesystem type or None
    :rtype: str or None
    """
    for mount_point, fs_type in _get_mounts():
        if (mount_point == '/'
                or path == mount_point
                or path.startswith(mount_point + '/')):
            return fs_type
    return None


def should_skip_file_metadata(path):
    """Determine if file metadata collection should be skipped for a
    file.

    Metadata collection is skipped entirely for files on:
    - Pseudo filesystems (proc, sysfs, debugfs, etc)
    - Network filesystems (nfs, nfs4, cifs, etc)

    :param path: The filesystem path to check
    :type path: str

    :returns: True if metadata should be skipped
    :rtype: bool
    """
    fs_type = _get_filesystem_type(path)
    return fs_type in SKIP_FS_TYPES if fs_type else False


def get_file_hash(path, algorithm='sha256', max_size=None):
    """Calculate the hash of a file for content comparison.

    :param path: Path to the file to hash
    :type path: str

    :param algorithm: Hash algorithm to use (default: sha256)
    :type algorithm: str

    :param max_size: Maximum file size to hash in bytes
        (default: 10MB)
    :type max_size: int or None

    :returns: Hexadecimal hash string or None if file is too
        large or we got an error
    :rtype: str or None
    """
    if max_size is None:
        max_size = HASH_SIZE_LIMIT

    try:
        file_size = os.path.getsize(path)
        if file_size > max_size:
            log.debug(
                f"Skipping hash for '{path}': size {file_size} "
                f"exceeds limit {max_size}"
            )
            return None

        hash_ctx = hashlib.new(algorithm)
        with open(path, 'rb') as f:
            while chunk := f.read(65536):
                hash_ctx.update(chunk)
        return hash_ctx.hexdigest()
    except OSError as e:
        log.debug(f"Failed to hash '{path}': {e}")
        return None


def collect_file_metadata(path, file_stat=None, known_hash=None):
    """Collect comprehensive file metadata for snapshot comparison.

    Collects file metadata including size, timestamps, permissions,
    ownership, SELinux context, and (for critical files) content
    hash.

    :param path: The filesystem path to collect metadata for
    :type path: str

    :param file_stat: Optional pre-computed stat object to avoid
        re-stat
    :type file_stat: os.stat_result or None

    :param known_hash: Pre-computed sha256 to reuse instead of
        re-reading the file (e.g. when a file was found unchanged
        and its hash is already known from the previous snapshot)
    :type known_hash: str or None

    :returns: Dictionary of file metadata or None on error
    :rtype: dict or None
    """
    if file_stat is None:
        try:
            file_stat = os.lstat(path)
        except OSError as e:
            log.debug(f"Failed to stat '{path}': {e}")
            return None

    metadata = {
        "path": path.lstrip('/'),
        "source_path": path,
        "size": file_stat.st_size,
        "mtime_ns": file_stat.st_mtime_ns,
        "ctime_ns": file_stat.st_ctime_ns,
        "mode": format(stat.S_IMODE(file_stat.st_mode), '04o'),
        "uid": file_stat.st_uid,
        "gid": file_stat.st_gid,
    }

    try:
        if pwd:
            metadata["owner"] = pwd.getpwuid(
                file_stat.st_uid).pw_name
        if grp:
            metadata["group"] = grp.getgrgid(
                file_stat.st_gid).gr_name
    except (KeyError, OSError):
        # The uid/gid may not map to a name (deleted account, NSS
        # lookup failure). We already recorded the numeric uid/gid,
        # so the owner/group names are optional and we skip them.
        pass

    if stat.S_ISREG(file_stat.st_mode):
        metadata["file_type"] = "file"
    elif stat.S_ISDIR(file_stat.st_mode):
        metadata["file_type"] = "directory"
    elif stat.S_ISBLK(file_stat.st_mode):
        metadata["file_type"] = "block_device"
    elif stat.S_ISCHR(file_stat.st_mode):
        metadata["file_type"] = "char_device"
    elif stat.S_ISFIFO(file_stat.st_mode):
        metadata["file_type"] = "fifo"
    elif stat.S_ISLNK(file_stat.st_mode):
        metadata["file_type"] = "symlink"
        try:
            metadata["link_target"] = os.readlink(path)
        except OSError:
            # Symlink target is best-effort; if it can't be read we
            # still keep the "symlink" file_type and move on.
            pass
    elif stat.S_ISSOCK(file_stat.st_mode):
        metadata["file_type"] = "socket"
    else:
        metadata["file_type"] = "unknown"

    if selinux_enabled:
        try:
            context = selinux.lgetfilecon(path)
            if context and len(context) > 1:
                metadata["selinux_context"] = context[1]
        except OSError:
            # The context is best-effort; if the lookup fails we skip
            # the selinux_context field and keep the rest of the record.
            pass

    if stat.S_ISREG(file_stat.st_mode):
        if any(path.startswith(cpath)
               for cpath in HASH_CRITICAL_PATHS):
            file_hash = known_hash or get_file_hash(path)
            if file_hash:
                metadata["sha256"] = file_hash

    return metadata


def file_changed(path, current_stat, prev_meta):
    """Check if a file has changed compared to previous snapshot.

    :param path: The filesystem path to check
    :type path: str

    :param current_stat: Current stat result for the file
    :type current_stat: os.stat_result

    :param prev_meta: Previous snapshot metadata dict for
        comparison
    :type prev_meta: dict

    :returns: True if the file has changed
    :rtype: bool
    """
    current_type = next(
        (type_name for check, type_name in _FILE_TYPE_MAP.items()
         if check(current_stat.st_mode)), "unknown")
    if current_type != prev_meta.get('file_type'):
        return True

    if current_stat.st_size != prev_meta.get('size'):
        return True
    if current_stat.st_mtime_ns != prev_meta.get('mtime_ns'):
        return True
    # ctime catches metadata-only changes (chmod, chown, rename) that
    # mtime misses, so we re-collect on it. It is left out of "sos
    # compare" on purpose, to avoid ctime-only noise in the diff.
    # TODO: consider showing ctime in compare later, carefully.
    if current_stat.st_ctime_ns != prev_meta.get('ctime_ns'):
        return True
    current_mode = format(
        stat.S_IMODE(current_stat.st_mode), '04o')
    if current_mode != prev_meta.get('mode'):
        return True
    if current_stat.st_uid != prev_meta.get('uid'):
        return True
    if current_stat.st_gid != prev_meta.get('gid'):
        return True
    # uid/gid are compared numerically, so ownership changes are caught.
    # TODO: owner/group names can change while uid/gid stay the same
    # (a rename in /etc/passwd); comparing names too would catch that.
    # A relabel (restorecon) changes the SELinux context. On most
    # filesystems that also bumps ctime, so the ctime check above
    # already catches it, but since that is not guaranteed everywhere
    # we compare the context directly as a backstop and re-collect
    # when it differs.
    if selinux_enabled and 'selinux_context' in prev_meta:
        try:
            context = selinux.lgetfilecon(path)
            current_context = (context[1] if context and len(context) > 1
                               else None)
        except OSError:
            current_context = None
        if current_context != prev_meta.get('selinux_context'):
            return True
    if prev_meta.get('file_type') == 'symlink':
        try:
            current_target = os.readlink(path)
        except OSError:
            return True
        if current_target != prev_meta.get('link_target'):
            return True
    if any(path.startswith(prefix) for prefix in HASH_CRITICAL_PATHS):
        prev_hash = prev_meta.get('sha256')
        if prev_hash is not None:
            current_hash = get_file_hash(path)
            if current_hash is None:
                return True
            if current_hash != prev_hash:
                return True
    return False


def _path_matches(path, patterns):
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def dict_at(data, *keys):
    """Retrn the nested dict at data[k1][k2]..., or {} if any
    level is missing or not a dict.  Never raise on malformed manifest
    input (a snapshot whose JSON parses but is the wrong shape).

    :param data: The (maybe untrusted) parsed manifest
    :type data: dict

    :param keys: Successive dict keys to descend through
    :type keys: str

    :returns: The nested dict, or an empty dict
    :rtype: dict
    """
    for key in keys:
        if not isinstance(data, dict):
            return {}
        data = data.get(key)
    return data if isinstance(data, dict) else {}


def extract_files_metadata(manifest_data, profiles=None,
                           include=None, exclude=None):
    """Walk manifest JSON and return dict keyed by source_path.

    Walks components.report.plugins.<plugin>.files[*].files_metadata[*]
    and return {source_path: metadata_dict}.

    If we find amalformed manifest, i.e. any level that is missing or has an
    unexpected type, is skipped rather than raising, so a corrupt snapshot
    throws an empty result instead of a traceback.

    :param manifest_data: Parsed snapshot manifest JSON
    :type manifest_data: dict

    :param profiles: If given, only include files from plugins whose
                     profiles list intersects with this set.
    :type profiles: list or None

    :param include:  If given, only include files whose source_path
                     matches at least one glob pattern.
    :type include: list or None

    :param exclude:  If given, skip files whose source_path matches
                     any glob pattern.
    :type exclude: list or None

    :returns: Mapping of source_path to file metadata dict
    :rtype: dict
    """
    result = {}
    plugins = dict_at(manifest_data, 'components', 'report', 'plugins')
    filter_profiles = set(profiles) if profiles else None
    for plugin in plugins.values():
        if not isinstance(plugin, dict):
            continue
        if filter_profiles:
            plugin_profiles = set(plugin.get('profiles', []))
            if not plugin_profiles & filter_profiles:
                continue
        files = plugin.get('files', [])
        if not isinstance(files, list):
            continue
        for file_entry in files:
            if not isinstance(file_entry, dict):
                continue
            metas = file_entry.get('files_metadata', [])
            if not isinstance(metas, list):
                continue
            for meta in metas:
                if not isinstance(meta, dict):
                    continue
                source_path = meta.get('source_path')
                if not source_path:
                    continue
                if include and not _path_matches(source_path, include):
                    continue
                if exclude and _path_matches(source_path, exclude):
                    continue
                result[source_path] = meta
    return result

# vim: set et ts=4 sw=4 :
