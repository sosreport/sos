# This file is part of the sos project: https://github.com/sosreport/sos

"""Bounded sanitizer for rotated Corosync text logs."""

import datetime
import gzip
import io
import re
import zlib

from sos.cleaner.text import sanitize_stream


class CorosyncLogError(Exception):
    """A safe Corosync log failure with optional category/path metadata."""

    def __init__(self, message='Corosync log processing failed',
                 category=None, relative_path=None):
        self.category = category
        self.relative_path = (tuple(relative_path)
                              if relative_path is not None else None)
        super().__init__(message)


class CorosyncLog:
    """Recognize and transform only the approved Corosync logfile family."""

    MAX_COMPRESSED = 16 * 1024 * 1024
    MAX_DECOMPRESSED = 128 * 1024 * 1024
    MAX_RATIO = 200
    RATIO_FLOOR = 1 * 1024 * 1024
    MAX_MEMBERS = 1024
    MAX_AGGREGATE = 1 * 1024 * 1024 * 1024
    _path = re.compile(
        r'var/log/cluster/corosync\.log-([0-9]{4})([0-9]{2})([0-9]{2})\.gz\Z')

    @classmethod
    def is_path(cls, relative):
        parts = tuple(relative)
        candidates = (parts, parts[1:] if len(parts) > 1 else ())
        return any(cls._path_date(candidate) is not None
                   for candidate in candidates)

    @classmethod
    def _path_date(cls, parts):
        if len(parts) != 4 or parts[:3] != ('var', 'log', 'cluster'):
            return None
        match = cls._path.fullmatch('/'.join(parts))
        if not match:
            return None
        try:
            return datetime.date(*(int(value) for value in match.groups()))
        except ValueError:
            return None

    @classmethod
    def decode(cls, source, compressed_size):
        if not isinstance(compressed_size, int) or not (
                0 < compressed_size <= cls.MAX_COMPRESSED):
            raise CorosyncLogError('compressed size limit')
        first = source.read(3)
        if first != b'\x1f\x8b\x08':
            raise CorosyncLogError('gzip signature')
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        output = bytearray()
        consumed = 0
        eof_seen = False
        chunk = first
        while True:
            if not chunk:
                chunk = source.read(64 * 1024)
            if not chunk:
                break
            consumed += len(chunk)
            if consumed > compressed_size or eof_seen:
                raise CorosyncLogError('trailing or oversized gzip')
            try:
                remaining = cls.MAX_DECOMPRESSED - len(output)
                output.extend(decoder.decompress(chunk, remaining + 1))
            except zlib.error:
                raise CorosyncLogError('gzip decode') from None
            if (len(output) >= cls.MAX_DECOMPRESSED and
                    not decoder.eof) or len(output) > cls.MAX_DECOMPRESSED or \
                    len(output) > max(cls.RATIO_FLOOR,
                                      compressed_size * cls.MAX_RATIO):
                raise CorosyncLogError('decompressed size limit')
            if decoder.eof:
                eof_seen = True
                if decoder.unused_data:
                    raise CorosyncLogError('trailing gzip data')
            chunk = b''
        if consumed != compressed_size or not decoder.eof or \
                decoder.unconsumed_tail or decoder.unused_data:
            raise CorosyncLogError('truncated or trailing gzip data')
        return bytes(output)

    @classmethod
    def sanitize(cls, source, compressed_size, session, destination=None,
                 on_decoded=None, residual_check=None):
        payload = cls.decode(source, compressed_size)
        try:
            payload.decode('utf-8')
        except UnicodeError:
            raise CorosyncLogError('non-UTF-8 log') from None
        if on_decoded is not None:
            on_decoded(len(payload))
        output = io.BytesIO()
        try:
            sanitize_stream(io.BytesIO(payload), output, session=session,
                            redactor=session.new_stream_redactor())
        except CorosyncLogError:
            raise
        except Exception:
            raise CorosyncLogError('text sanitization') from None
        sanitized = output.getvalue()
        if residual_check is not None:
            try:
                residual_check(sanitized)
            except CorosyncLogError:
                raise
            except Exception:
                raise CorosyncLogError('residual privacy') from None
        if destination is not None:
            destination.write(sanitized)
        return sanitized

    @staticmethod
    def encode(payload):
        result = gzip.compress(payload, compresslevel=9, mtime=0)
        if result[3] != 0:
            raise CorosyncLogError('non-deterministic gzip header')
        return result


class PacemakerLog(CorosyncLog):
    """The separately approved rotated Pacemaker detail-log family."""

    _path = re.compile(
        r'var/log/pacemaker/pacemaker\.log-([0-9]{4})([0-9]{2})([0-9]{2})\.gz\Z')

    @classmethod
    def _path_date(cls, parts):
        if len(parts) != 4 or parts[:3] != ('var', 'log', 'pacemaker'):
            return None
        match = cls._path.fullmatch('/'.join(parts))
        if not match:
            return None
        try:
            return datetime.date(*(int(value) for value in match.groups()))
        except ValueError:
            return None
