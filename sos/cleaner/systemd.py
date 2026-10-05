"""Exact systemd-coredump helper omission policy."""

import os
import struct


PATH = ('usr', 'lib', 'systemd', 'systemd-coredump')
MAX_SIZE = 16 * 1024 * 1024


def is_path(relative):
    parts = tuple(relative)
    return parts == PATH or (len(parts) == len(PATH) + 1 and
                             parts[1:] == PATH)


def classify_fd(fd, observed):
    if not (stat_is_regular(observed.st_mode) and observed.st_nlink == 1 and
            52 <= observed.st_size <= MAX_SIZE):
        return 'reject'
    try:
        ident = os.pread(fd, 16, 0)
    except (AttributeError, OSError):
        return 'reject'
    if len(ident) < 16 or ident[:4] != b'\x7fELF' or ident[6] != 1:
        return 'reject'
    elf_class, data = ident[4], ident[5]
    if elf_class not in (1, 2) or data not in (1, 2):
        return 'reject'
    endian = '<' if data == 1 else '>'
    header_size = 52 if elf_class == 1 else 64
    if observed.st_size < header_size:
        return 'reject'
    try:
        header = os.pread(fd, header_size, 0)
        if len(header) != header_size:
            return 'reject'
        if elf_class == 1:
            fields = struct.unpack_from(endian + 'HHIIIIIHHHHHH', header, 16)
            etype, _machine, _version, _entry, phoff, shoff, _flags, ehsize, phentsize, phnum, shentsize, shnum, shstrndx = fields
        else:
            fields = struct.unpack_from(endian + 'HHIQQQIHHHHHH', header, 16)
            etype, _machine, _version, _entry, phoff, shoff, _flags, ehsize, phentsize, phnum, shentsize, shnum, shstrndx = fields
        if etype not in (2, 3) or ehsize != header_size:
            return 'reject'
        if phnum and (phentsize == 0 or phoff + phnum * phentsize > observed.st_size):
            return 'reject'
        if shnum and (shentsize == 0 or shoff + shnum * shentsize > observed.st_size):
            return 'reject'
        if shstrndx >= shnum and shstrndx != 0:
            return 'reject'
    except (struct.error, OverflowError):
        return 'reject'
    return 'omit'


def stat_is_regular(mode):
    return (mode & 0o170000) == 0o100000
