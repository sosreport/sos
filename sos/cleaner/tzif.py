# This file is part of the sos project: https://github.com/sosreport/sos

"""Bounded TZif framing checks for narrowly approved report artifacts."""

import os
import struct


DEFAULT_MAX_TZIF_SIZE = 1024 * 1024
_HEADER_SIZE = 44
_SUPPORTED_VERSIONS = (b'2', b'3', b'4')
_MAX_COUNT = 1_000_000


def _header(data, offset, version):
    if offset + _HEADER_SIZE > len(data):
        return None
    if data[offset:offset + 4] != b'TZif':
        return None
    if data[offset + 4:offset + 5] != version:
        return None
    counts = struct.unpack('>6I', data[offset + 20:offset + 44])
    if any(value > _MAX_COUNT for value in counts):
        return None
    ttisgmtcnt, ttisstdcnt, leapcnt, timecnt, typecnt, charcnt = counts
    if typecnt == 0 or typecnt > 256 or charcnt > _MAX_COUNT:
        return None
    # TZif stores one indicator per local-time type, not per transition.
    # Implementations commonly use either zero indicators or one per type.
    if ttisgmtcnt not in (0, typecnt) or ttisstdcnt not in (0, typecnt):
        return None
    return counts


def _block_size(counts, time_size):
    ttisgmtcnt, ttisstdcnt, leapcnt, timecnt, typecnt, charcnt = counts
    return (timecnt * time_size + timecnt + typecnt * 6 + charcnt +
            leapcnt * (time_size + 4) + ttisstdcnt + ttisgmtcnt)


def _valid_block(data, offset, counts, time_size):
    size = _block_size(counts, time_size)
    end = offset + size
    if end > len(data):
        return None
    _, _, _, timecnt, typecnt, charcnt = counts
    index_start = offset + timecnt * time_size
    indexes = data[index_start:index_start + timecnt]
    if any(index >= typecnt for index in indexes):
        return None
    ttinfo_start = index_start + timecnt
    for index in range(typecnt):
        ttinfo = ttinfo_start + index * 6
        isdst = data[ttinfo + 4]
        abbrind = data[ttinfo + 5]
        if isdst not in (0, 1) or abbrind >= charcnt:
            return None
    return end


def is_tzif_fd(fd, max_size=DEFAULT_MAX_TZIF_SIZE):
    """Return whether *fd* is a complete, bounded supported TZif file."""
    try:
        initial = os.fstat(fd)
        if not stat_is_regular(initial.st_mode) or initial.st_size < _HEADER_SIZE:
            return False
        if initial.st_size > max_size:
            return False
        os.lseek(fd, 0, os.SEEK_SET)
        data = bytearray()
        while len(data) < initial.st_size:
            chunk = os.read(fd, min(64 * 1024, initial.st_size - len(data)))
            if not chunk:
                return False
            data.extend(chunk)
        if len(data) != initial.st_size:
            return False
        version = bytes(data[4:5])
        if version not in _SUPPORTED_VERSIONS:
            return False
        first = _header(data, 0, version)
        if first is None:
            return False
        offset = _valid_block(data, _HEADER_SIZE, first, 4)
        if offset is None:
            return False
        second = _header(data, offset, version)
        if second is None:
            return False
        offset = _valid_block(data, offset + _HEADER_SIZE, second, 8)
        if offset is None or offset >= len(data):
            return False
        # Version 2+ files carry a POSIX TZ string after the second block.
        footer = bytes(data[offset:])
        return footer.startswith(b'\n') and footer.endswith(b'\n')
    except (OSError, OverflowError, ValueError, struct.error):
        return False
    finally:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
        except OSError:
            pass


def stat_is_regular(mode):
    return (mode & 0o170000) == 0o100000
