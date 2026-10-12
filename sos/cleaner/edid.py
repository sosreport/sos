# This file is part of the sos project: https://github.com/sosreport/sos

"""Narrow DRM connector EDID classification for report sanitization."""

import os
import re
import stat


class DrmEdidPolicy:
    """Recognize and validate only connector EDID report members."""

    MAX_SIZE = 4096
    BLOCK_SIZE = 128
    _card = r'(?:0|[1-9][0-9]*)'
    _connector = re.compile(
        r'[A-Za-z0-9][A-Za-z0-9-]{0,63}-[1-9][0-9]*(?:-[1-9][0-9]*)*\Z')
    _card_connector = re.compile(r'card(' + _card + r')-(.+)\Z')

    @classmethod
    def _candidates(cls, relative):
        parts = tuple(relative)
        candidates = [parts]
        if len(parts) > 1:
            candidates.append(parts[1:])
        return candidates

    @classmethod
    def is_path(cls, relative):
        """Return whether *relative* is an approved EDID path."""
        return any(cls._is_class_path(candidate) or
                   cls._is_device_path(candidate)
                   for candidate in cls._candidates(relative))

    @classmethod
    def _split_card_connector(cls, component):
        match = cls._card_connector.fullmatch(component)
        if not match or not cls._connector.fullmatch(match.group(2)):
            return None
        return match.group(1), match.group(2)

    @classmethod
    def _is_class_path(cls, parts):
        if len(parts) != 5 or parts[:3] != ('sys', 'class', 'drm') or \
                parts[-1] != 'edid':
            return False
        return cls._split_card_connector(parts[3]) is not None

    @classmethod
    def _is_device_component(cls, component):
        return bool(component) and component not in ('.', '..') and \
            '\x00' not in component and '/' not in component and \
            '\\' not in component and component.isascii()

    @classmethod
    def _is_device_path(cls, parts):
        if len(parts) < 7 or parts[0] != 'sys' or parts[1] != 'devices' or \
                parts[-1] != 'edid' or parts[-4] != 'drm':
            return False
        device_path = parts[2:-4]
        if not (1 <= len(device_path) <= 32) or not all(
                cls._is_device_component(part) for part in device_path):
            return False
        card = parts[-3]
        connector_card = cls._split_card_connector(parts[-2])
        if connector_card is None or card != 'card' + connector_card[0]:
            return False
        return True

    @classmethod
    def classify_fd(cls, fd, observed):
        """Return ``omit`` or ``reject`` after bounded structural checking."""
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            return 'reject'
        if observed.st_size == 0:
            return 'omit'
        if observed.st_size < cls.BLOCK_SIZE or \
                observed.st_size > cls.MAX_SIZE or \
                observed.st_size % cls.BLOCK_SIZE:
            return 'reject'
        try:
            payload = os.pread(fd, observed.st_size, 0)
            current = os.fstat(fd)
        except (AttributeError, OSError):
            return 'reject'
        if (current.st_dev, current.st_ino, current.st_size) != \
                (observed.st_dev, observed.st_ino, observed.st_size):
            return 'reject'
        if len(payload) != observed.st_size or \
                payload[:8] != b'\x00\xff\xff\xff\xff\xff\xff\x00':
            return 'reject'
        blocks = observed.st_size // cls.BLOCK_SIZE
        if payload[126] != blocks - 1:
            return 'reject'
        # Checksum validity is diagnostic only; malformed EDIDs remain useful
        # evidence and therefore do not prevent omission.
        for offset in range(0, observed.st_size, cls.BLOCK_SIZE):
            _checksum_valid = (sum(payload[offset:offset + cls.BLOCK_SIZE]) &
                               0xff) == 0
        return 'omit'
