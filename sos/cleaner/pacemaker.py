# This file is part of the sos project: https://github.com/sosreport/sos

"""Bounded, privacy-aware handling of Pacemaker scheduler inputs."""

import bz2
import io
import re
import xml.etree.ElementTree as ET
from xml.parsers import expat

from sos.cleaner.text import sanitize_stream


class PacemakerSchedulerInputError(Exception):
    """A scheduler input failed its bounded format or privacy checks."""


class PacemakerSchedulerInput:
    """Pure helpers for the narrowly scoped pe-input artifact family."""

    MAX_COMPRESSED = 16 * 1024 * 1024
    MAX_DECOMPRESSED = 128 * 1024 * 1024
    MAX_RATIO = 200
    RATIO_FLOOR = 1024 * 1024
    MAX_MEMBERS = 10000
    MAX_TOTAL_DECOMPRESSED = 1024 * 1024 * 1024
    MAX_ELEMENTS = 1000000
    MAX_DEPTH = 256
    MAX_ATTRIBUTES_PER_ELEMENT = 128
    MAX_ATTRIBUTES = 4000000
    MAX_ATTRIBUTE_LENGTH = 1024 * 1024
    MAX_TEXT_LENGTH = 8 * 1024 * 1024
    REDACTED = '[REDACTED_SECRET]'
    _path = re.compile(
        r'^sos_commands/pacemaker/crm_report/([^/]+)/pengine/'
        r'pe-input-(0|[1-9][0-9]*)\.bz2$')
    _secret = re.compile(
        r'^(?:pass(?:word|wd)?|pwd|token|secret|credential|community|'
        r'auth|authentication|api(?:key|[_-]key)|private(?:key|[_-]key)|'
        r'access(?:key|[_-]key)|secret(?:key|[_-]key))$')

    @classmethod
    def sequence_for_path(cls, relative):
        """Return the sequence number, or None for an unapproved path."""
        if isinstance(relative, (tuple, list)):
            parts = tuple(relative)
            if len(parts) == 7:
                parts = parts[1:]
            path = '/'.join(parts)
        else:
            path = relative
            parts = tuple(path.split('/'))
            if len(parts) == 7:
                path = '/'.join(parts[1:])
                parts = tuple(path.split('/'))
        match = cls._path.fullmatch(path)
        if not match:
            return None
        node = match.group(1)
        if (not node or node in ('.', '..') or '\\' in node or
                not node.isascii()):
            return None
        sequence = int(match.group(2))
        if sequence > 2147483647:
            return None
        return sequence

    @classmethod
    def is_path(cls, relative):
        return cls.sequence_for_path(relative) is not None

    @classmethod
    def _append_checked(cls, output, chunk, compressed_size):
        output.extend(chunk)
        if len(output) > cls.MAX_DECOMPRESSED:
            raise PacemakerSchedulerInputError('decompressed size limit')
        if len(output) > max(cls.RATIO_FLOOR,
                             compressed_size * cls.MAX_RATIO):
            raise PacemakerSchedulerInputError('compression ratio limit')

    @classmethod
    def decode(cls, source, compressed_size):
        if not (0 < compressed_size <= cls.MAX_COMPRESSED):
            raise PacemakerSchedulerInputError('compressed size limit')
        first = source.read(4)
        if len(first) != 4 or not first.startswith(b'BZh') or \
                first[3] not in b'123456789':
            raise PacemakerSchedulerInputError('bzip2 signature')
        decoder = bz2.BZ2Decompressor()
        output = bytearray()
        consumed = 4
        try:
            data = decoder.decompress(first)
        except (OSError, EOFError):
            raise PacemakerSchedulerInputError('bzip2 decode') from None
        cls._append_checked(output, data, compressed_size)
        while not decoder.eof:
            chunk = source.read(64 * 1024)
            if not chunk:
                break
            consumed += len(chunk)
            if consumed > compressed_size:
                raise PacemakerSchedulerInputError('compressed size')
            try:
                data = decoder.decompress(chunk)
            except (OSError, EOFError):
                raise PacemakerSchedulerInputError('bzip2 decode') from None
            cls._append_checked(output, data, compressed_size)
            if decoder.eof:
                if decoder.unused_data or source.read(1):
                    raise PacemakerSchedulerInputError('trailing bzip2 data')
                break
        if not decoder.eof or consumed != compressed_size:
            raise PacemakerSchedulerInputError('truncated bzip2 stream')
        return bytes(output)

    @classmethod
    def _validate_xml_limits(cls, payload):
        if not payload or b'\0' in payload:
            raise PacemakerSchedulerInputError('invalid XML bytes')
        parser = expat.ParserCreate()
        state = {'elements': 0, 'depth': 0, 'attributes': 0,
                 'text_lengths': []}

        def start(_name, attrs):
            state['elements'] += 1
            state['depth'] += 1
            state['text_lengths'].append(0)
            state['attributes'] += len(attrs)
            if (state['elements'] > cls.MAX_ELEMENTS or
                    state['depth'] > cls.MAX_DEPTH or
                    len(attrs) > cls.MAX_ATTRIBUTES_PER_ELEMENT or
                    state['attributes'] > cls.MAX_ATTRIBUTES):
                raise PacemakerSchedulerInputError('XML limits')
            if any(len(value) > cls.MAX_ATTRIBUTE_LENGTH
                   for value in attrs.values()):
                raise PacemakerSchedulerInputError('XML attribute limit')

        def end(_name):
            state['text_lengths'].pop()
            state['depth'] -= 1

        def text(value):
            if not state['text_lengths']:
                raise PacemakerSchedulerInputError('XML text placement')
            state['text_lengths'][-1] += len(value)
            if state['text_lengths'][-1] > cls.MAX_TEXT_LENGTH:
                raise PacemakerSchedulerInputError('XML text limit')

        def forbidden(*_args):
            raise PacemakerSchedulerInputError('XML declaration')

        parser.StartElementHandler = start
        parser.EndElementHandler = end
        parser.CharacterDataHandler = text
        parser.StartDoctypeDeclHandler = forbidden
        parser.EntityDeclHandler = forbidden
        parser.ExternalEntityRefHandler = forbidden
        try:
            parser.Parse(payload, True)
            root = ET.fromstring(payload)
        except PacemakerSchedulerInputError:
            raise
        except (expat.ExpatError, UnicodeError, ValueError):
            raise PacemakerSchedulerInputError('invalid CIB XML') from None
        if root.tag.rsplit('}', 1)[-1] != 'cib' or root.tag != 'cib':
            raise PacemakerSchedulerInputError('CIB root required')
        return root

    @classmethod
    def _is_secret_name(cls, name):
        tokens = re.findall(r'[A-Za-z0-9]+', name)
        if any(cls._secret.fullmatch(token.lower()) for token in tokens):
            return True
        joined = ''.join(tokens).lower()
        return any(joined.endswith(value) for value in (
            'apikey', 'accesskey', 'privatekey', 'secretkey'))

    @classmethod
    def redact_credentials(cls, root):
        for element in root.iter():
            if element.tag.rsplit('}', 1)[-1] == 'nvpair':
                name = element.attrib.get('name', '')
                if 'value' in element.attrib and cls._is_secret_name(name):
                    element.set('value', cls.REDACTED)
            for name in tuple(element.attrib):
                if name != 'value' and cls._is_secret_name(name):
                    element.set(name, cls.REDACTED)

    @classmethod
    def prepare(cls, payload):
        root = cls._validate_xml_limits(payload)
        cls.redact_credentials(root)
        return ET.tostring(root, encoding='utf-8', short_empty_elements=True)

    @classmethod
    def sanitize(cls, source, compressed_size, session, destination=None):
        payload = cls.decode(source, compressed_size)
        intermediate = cls.prepare(payload)
        output = io.BytesIO()
        sanitize_stream(io.BytesIO(intermediate), output, session=session,
                        redactor=session.new_stream_redactor())
        sanitized = output.getvalue()
        cls._validate_xml_limits(sanitized)
        root = ET.fromstring(sanitized)
        cls._assert_credentials_redacted(root)
        if destination is not None:
            destination.write(sanitized)
        return sanitized

    @classmethod
    def _assert_credentials_redacted(cls, root):
        for element in root.iter():
            if element.tag.rsplit('}', 1)[-1] == 'nvpair':
                if (cls._is_secret_name(element.attrib.get('name', '')) and
                        element.attrib.get('value') != cls.REDACTED):
                    raise PacemakerSchedulerInputError('credential residual')

    @classmethod
    def encode(cls, payload):
        return bz2.compress(payload, compresslevel=9)

    @classmethod
    def residual_check(cls, payload):
        root = cls._validate_xml_limits(payload)
        cls._assert_credentials_redacted(root)
