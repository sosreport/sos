# This file is part of the sos project: https://github.com/sosreport/sos

"""Bounded OpenPGP packet framing checks for sanitizer policy decisions."""

import os
import stat


DEFAULT_MAX_KEYRING_SIZE = 16 * 1024 * 1024


def _read_exact(fd, size):
    """Read exactly *size* bytes, returning None on premature EOF."""
    chunks = []
    remaining = size
    while remaining:
        chunk = os.read(fd, remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def _packet_length(fd, header):
    """Return a packet body length, or None for unsupported framing."""
    if header & 0x40:  # new-format packet header
        first = _read_exact(fd, 1)
        if first is None:
            return None
        first = first[0]
        if first < 192:
            return first
        if first < 224:
            second = _read_exact(fd, 1)
            if second is None:
                return None
            return ((first - 192) << 8) + second[0] + 192
        if first == 255:
            raw_length = _read_exact(fd, 4)
            if raw_length is None:
                return None
            return int.from_bytes(raw_length, 'big')
        # Partial body lengths are deliberately unsupported.  They make a
        # bounded, complete classification needlessly subtle.
        return None

    # old-format packet header
    length_type = header & 0x03
    if length_type == 0:
        raw_length = _read_exact(fd, 1)
        return None if raw_length is None else raw_length[0]
    if length_type == 1:
        raw_length = _read_exact(fd, 2)
        return None if raw_length is None else int.from_bytes(raw_length, 'big')
    if length_type == 2:
        raw_length = _read_exact(fd, 4)
        return None if raw_length is None else int.from_bytes(raw_length, 'big')
    # Indeterminate-length packets are not safe for this bounded classifier.
    return None


def is_public_keyring_fd(fd, max_size=DEFAULT_MAX_KEYRING_SIZE):
    """Return whether *fd* is a bounded, public-only OpenPGP keyring.

    Only packet headers and lengths are interpreted.  Packet bodies are never
    decoded or returned.  A complete packet stream containing at least one
    Public-Key packet is required; Secret-Key and Secret-Subkey packets are
    always rejected.
    """
    try:
        initial = os.fstat(fd)
        if not stat_is_regular(initial.st_mode) or initial.st_size < 0 or \
                initial.st_size > max_size:
            return False
        file_size = initial.st_size
        os.lseek(fd, 0, os.SEEK_SET)
        public_key_seen = False
        offset = 0
        while offset < file_size:
            header_bytes = _read_exact(fd, 1)
            if header_bytes is None:
                return False
            header = header_bytes[0]
            offset += 1
            if not header & 0x80:
                return False
            tag = (header & 0x3f) if header & 0x40 else (header >> 2) & 0x0f
            if tag in (5, 7):  # Secret-Key / Secret-Subkey
                return False
            body_length = _packet_length(fd, header)
            if body_length is None:
                return False
            if tag == 6 and body_length == 0:
                return False
            length_bytes = os.lseek(fd, 0, os.SEEK_CUR) - offset
            offset += length_bytes + body_length
            if offset > file_size:
                return False
            os.lseek(fd, body_length, os.SEEK_CUR)
            if tag == 6:  # Public-Key
                public_key_seen = True
        final = os.fstat(fd)
        return public_key_seen and final.st_size == file_size
    except (OSError, OverflowError, ValueError):
        return False
    finally:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
        except OSError:
            pass


def stat_is_regular(mode):
    """Keep the classifier's filesystem-type check local and explicit."""
    return stat.S_ISREG(mode)
