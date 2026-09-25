# This file is part of the sos project: https://github.com/sosreport/sos

"""Bounded, token-aware handling of authoritative SELinux CIL modules."""

import bz2
import io
import re

from sos.cleaner.text import sanitize_stream


class DirectCilError(Exception):
    """A direct-CIL object failed its bounded syntax/privacy checks."""


class DirectCil:
    """Helpers for the one explicitly identified direct-CIL artifact family."""

    MAX_COMPRESSED = 16 * 1024 * 1024
    MAX_SOURCE = 64 * 1024 * 1024
    MAX_RATIO = 200
    RATIO_FLOOR = 1024 * 1024
    MAX_TOKENS = 1000000
    MAX_DEPTH = 256
    MAX_TOKEN = 1024 * 1024
    MAX_COMMENT = 1024 * 1024
    MAX_STRING = 1024 * 1024
    _TOKEN = re.compile(r'[A-Za-z0-9_./:@%+\-]+')
    _PRIORITY = re.compile(r'[1-9][0-9]{0,2}\Z')
    _SAFE_EXTERNAL = re.compile(
        r'(?:[A-Za-z0-9_-]+\.)+[A-Za-z]{2,63}|'
        r'(?:\d{1,3}\.){3}\d{1,3}|'
        r'[0-9A-Fa-f]{0,4}:[0-9A-Fa-f:]{2,}')

    @classmethod
    def is_path(cls, relative):
        parts = tuple(relative)
        if len(parts) == 9:
            candidate = parts
        elif len(parts) == 10 and parts[0] not in ('', '.', '..'):
            candidate = parts[1:]
        else:
            return False
        if not (candidate[:6] == (
                    'var', 'lib', 'selinux', 'targeted', 'active', 'modules')
                and candidate[-1] == 'cil'):
            return False
        priority, module = candidate[6:8]
        return (cls._PRIORITY.fullmatch(priority) is not None and
                bool(module) and module not in ('.', '..') and
                len(module) <= 255 and
                not any(ord(char) < 0x20 or char in '/\\'
                        for char in module))

    @classmethod
    def decode(cls, source, compressed_size):
        if not (0 < compressed_size <= cls.MAX_COMPRESSED):
            raise DirectCilError('compressed size limit')
        data = source.read(compressed_size)
        if len(data) != compressed_size or not data.startswith(b'BZh'):
            raise DirectCilError('bzip2 input')
        try:
            decoder = bz2.BZ2Decompressor()
            payload = decoder.decompress(data)
        except (OSError, EOFError, ValueError):
            raise DirectCilError('bzip2 decode') from None
        if (not decoder.eof or decoder.unused_data or
                len(payload) > cls.MAX_SOURCE or
                len(payload) > max(cls.RATIO_FLOOR,
                                   compressed_size * cls.MAX_RATIO)):
            raise DirectCilError('bzip2 bounds')
        return payload

    @classmethod
    def _lex(cls, payload):
        try:
            text = payload.decode('utf-8')
        except UnicodeError:
            raise DirectCilError('invalid UTF-8') from None
        tokens = []
        depth = 0
        position = 0
        while position < len(text):
            char = text[position]
            if char.isspace():
                position += 1
                continue
            if char == ';':
                end = text.find('\n', position)
                end = len(text) if end < 0 else end
                if end - position > cls.MAX_COMMENT:
                    raise DirectCilError('comment limit')
                tokens.append(('comment', text[position:end]))
                position = end
            elif char in '()':
                depth += 1 if char == '(' else -1
                if depth < 0 or depth > cls.MAX_DEPTH:
                    raise DirectCilError('nesting limit')
                tokens.append(('punct', char))
                position += 1
            elif char == '"':
                end = position + 1
                escaped = False
                while end < len(text):
                    current = text[end]
                    if current == '"' and not escaped:
                        break
                    escaped = current == '\\' and not escaped
                    if current != '\\':
                        escaped = False
                    end += 1
                if end >= len(text):
                    raise DirectCilError('unterminated string')
                if end - position - 1 > cls.MAX_STRING:
                    raise DirectCilError('string limit')
                tokens.append(('string', text[position:end + 1]))
                position = end + 1
            else:
                match = cls._TOKEN.match(text, position)
                if not match:
                    raise DirectCilError('unsupported CIL lexical construct')
                value = match.group(0)
                if len(value) > cls.MAX_TOKEN:
                    raise DirectCilError('token limit')
                tokens.append(('word', value))
                position = match.end()
            if len(tokens) > cls.MAX_TOKENS:
                raise DirectCilError('token count limit')
        if depth:
            raise DirectCilError('unbalanced CIL')
        return tokens

    @classmethod
    def _sanitize_fragment(cls, value, session):
        output = io.StringIO()
        sanitize_stream(io.BytesIO(value.encode('utf-8')), output,
                        session=session, redactor=session.new_stream_redactor())
        return output.getvalue()

    @classmethod
    def transform(cls, payload, session):
        tokens = cls._lex(payload)
        output = []
        for kind, value in tokens:
            if kind == 'comment':
                output.append(cls._sanitize_fragment(value, session))
            elif kind == 'string':
                output.append('"' + cls._sanitize_fragment(value[1:-1], session)
                              + '"')
            elif kind == 'word' and cls._SAFE_EXTERNAL.search(value):
                output.append(session.sanitize_line(value))
            else:
                output.append(value)
        result = (' '.join(output)).encode('utf-8')
        cls._lex(result)
        return result

    @classmethod
    def residual_check(cls, payload, check_text):
        tokens = cls._lex(payload)
        for kind, value in tokens:
            if kind in ('comment', 'string'):
                check_text(value)
            elif kind == 'word' and cls._SAFE_EXTERNAL.search(value):
                check_text(value)

    @staticmethod
    def encode(payload):
        return bz2.compress(payload, compresslevel=9)
