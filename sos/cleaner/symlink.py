# This file is part of the sos project: https://github.com/sosreport/sos

"""Shared POSIX symlink-target validation for report archives."""

import posixpath
import re


_WINDOWS_DRIVE = re.compile(r'^[A-Za-z]:')
_WINDOWS_DOT_TRAVERSAL = (
    re.compile(r'(?:^|/)\.\.?\\'),
    re.compile(r'\\\.\.?(?:\\|/|$)'),
)


def validate_symlink_target(member_name, target):
    """Validate and return an archive symlink target unchanged.

    ``member_name`` is a POSIX archive member path.  Validation is lexical:
    no filesystem lookup or symlink dereference is performed.
    """
    if (not isinstance(target, str) or not target or '\x00' in target):
        raise ValueError
    if posixpath.isabs(target) or target.startswith('\\'):
        raise ValueError
    if _WINDOWS_DRIVE.match(target):
        raise ValueError
    if any(pattern.search(target) for pattern in _WINDOWS_DOT_TRAVERSAL):
        raise ValueError

    parent = posixpath.dirname(member_name)
    resolved = posixpath.normpath(posixpath.join(parent, target))
    if (posixpath.isabs(resolved) or resolved == '..' or
            resolved.startswith('../')):
        raise ValueError
    return target
