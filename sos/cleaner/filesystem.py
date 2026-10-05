# This file is part of the sos project: https://github.com/sosreport/sos

"""Small helpers for removing private sanitizer temporary trees."""

import os
import stat


def remove_private_tree(path):
    """Remove a private tree even when archive modes are not writable."""
    observed = os.lstat(path)
    if os.path.islink(path) or not os.path.isdir(path):
        os.unlink(path)
        return

    # These paths are sanitizer-owned temporary data.  Restore write/execute
    # permission on directories through verified descriptors only; fwalk does
    # not follow symlinks.  This does not alter any published report.
    if not stat.S_ISDIR(observed.st_mode):
        os.unlink(path)
        return
    root_flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | \
        getattr(os, 'O_NOFOLLOW', 0)
    root_fd = os.open(path, root_flags)
    try:
        os.fchmod(root_fd, 0o700)
    finally:
        os.close(root_fd)
    for _root, _directories, _files, directory_fd in os.fwalk(
            path, topdown=False, follow_symlinks=False):
        os.fchmod(directory_fd, 0o700)
    import shutil
    shutil.rmtree(path)
