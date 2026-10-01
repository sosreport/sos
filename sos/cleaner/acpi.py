"""Narrow ACPI firmware-table omission policy."""

import os
import struct


APPROVED_PATHS = frozenset((
    ('sys', 'firmware', 'acpi', 'tables', 'WAET'),
    ('sys', 'firmware', 'acpi', 'tables', 'SSDT'),
    ('sys', 'firmware', 'acpi', 'tables', 'MCFG'),
    ('sys', 'firmware', 'acpi', 'tables', 'FACS'),
    ('sys', 'firmware', 'acpi', 'tables', 'FACP'),
    ('sys', 'firmware', 'acpi', 'tables', 'DSDT'),
    ('sys', 'firmware', 'acpi', 'tables', 'APIC'),
))
MAX_SIZE = 1024 * 1024


def _candidate(relative):
    parts = tuple(relative)
    if parts in APPROVED_PATHS:
        return parts
    if len(parts) == 1 + len(next(iter(APPROVED_PATHS))) and \
            parts[1:] in APPROVED_PATHS:
        return parts[1:]
    return None


def is_path(relative):
    return _candidate(relative) is not None


def classify_fd(fd, observed, relative):
    candidate = _candidate(relative)
    if candidate is None:
        return None
    if not (stat_is_regular(observed.st_mode) and observed.st_nlink == 1 and
            0 < observed.st_size <= MAX_SIZE):
        return 'reject'
    try:
        header = os.pread(fd, min(observed.st_size, 36), 0)
    except (AttributeError, OSError):
        return 'reject'
    if len(header) < 8:
        return 'reject'
    signature = header[:4]
    expected = candidate[-1].encode('ascii')
    if signature != expected:
        return 'reject'
    if signature == b'FACS':
        if observed.st_size < 64:
            return 'reject'
        declared = struct.unpack_from('<I', header, 4)[0]
    else:
        if len(header) < 36:
            return 'reject'
        declared = struct.unpack_from('<I', header, 4)[0]
    if declared != observed.st_size:
        return 'reject'
    return 'omit'


def stat_is_regular(mode):
    return (mode & 0o170000) == 0o100000
