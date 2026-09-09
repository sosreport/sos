# This file is part of the sos project: https://github.com/sosreport/sos
#
# See the LICENSE file in the source distribution for license information.

"""Irreversible, text-only redaction. Never pass secret values to a map."""

import re


class SecretRedactor:
    """Keep only delimiter state across lines, never captured secret values.

    Assignments accept shell/config/JSON separators and quoted values. Bare
    values end at whitespace or common field delimiters. Unclosed quotes and
    private key blocks suppress subsequent content through their closing
    delimiter (or EOF), deliberately preferring redaction to disclosure.
    """

    _assignment = re.compile(
        r'''(?<![\w./-])(?P<prefix>(?:--)?["']?'''
        r'(?P<key>(?:[a-z0-9]+[_-])*'
        r'(?:password|passwd|pwd|token|api_key|api-key|apikey|secret))'
        r'''["']?[ \t]*[=:][ \t]*)(?P<quote>["']?)''', re.I
    )
    _bare = re.compile(r'[^\s,;&}\]\)<>"\']+')
    _begin = re.compile(r'-----BEGIN ((?:[A-Z0-9]+ )*PRIVATE KEY)-----')
    _bearer = re.compile(r'(?i)(\bBearer[ \t]+)[a-z0-9._~+/=-]+')
    _jwt = re.compile(
        r'(?<![\w-])eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.'
        r'[A-Za-z0-9_-]+(?![\w-])'
    )
    _aws = re.compile(r'(?<![A-Za-z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}'
                      r'(?![A-Za-z0-9])')
    _url = re.compile(r'(?i)(\b[a-z][a-z0-9+.-]*://)'
                      r'[^\s/@<>"\']+@')

    def __init__(self):
        self._pem_end = None
        self._quote = None

    @staticmethod
    def _line_ending(line):
        return line[len(line.rstrip('\r\n')):]

    def _quoted_end(self, line, start):
        # Escaped quotes do not terminate a shell/JSON-style value.
        escaped = False
        for position in range(start, len(line)):
            char = line[position]
            if char == self._quote and not escaped:
                return position
            escaped = char == '\\' and not escaped
        return None

    def redact(self, line):
        result = []
        position = 0
        while position < len(line):
            if self._pem_end:
                end = line.find(self._pem_end, position)
                if end < 0:
                    return ''.join(result) + self._line_ending(line)
                position = end + len(self._pem_end)
                self._pem_end = None
                continue
            if self._quote:
                end = self._quoted_end(line, position)
                if end is None:
                    return ''.join(result) + self._line_ending(line)
                result.append(self._quote)
                position = end + 1
                self._quote = None
                continue
            assignment = self._assignment.search(line, position)
            pem = self._begin.search(line, position)
            matches = [match for match in (assignment, pem) if match]
            if not matches:
                result.append(line[position:])
                break
            match = min(matches, key=lambda item: item.start())
            result.append(line[position:match.start()])
            position = match.end()
            if match is pem:
                result.append('[REDACTED_PRIVATE_KEY]')
                self._pem_end = '-----END ' + match[1] + '-----'
                continue
            key = match['key'].lower()
            marker = ('[REDACTED_TOKEN]' if key.endswith('token')
                      else '[REDACTED_SECRET]')
            result.append(match['prefix'] + match['quote'] + marker)
            if match['quote']:
                self._quote = match['quote']
            else:
                private_key = self._begin.match(line, position)
                if private_key:
                    self._pem_end = ('-----END ' + private_key[1]
                                     + '-----')
                    position = private_key.end()
                    continue
                bearer = self._bearer.match(line, position)
                if bearer:
                    position = bearer.end()
                    continue
                value = self._bare.match(line, position)
                if value:
                    position = value.end()
        line = ''.join(result)
        line = self._url.sub(r'\1[REDACTED_SECRET]@', line)
        line = self._bearer.sub(r'\1[REDACTED_TOKEN]', line)
        line = self._jwt.sub('[REDACTED_TOKEN]', line)
        return self._aws.sub('[REDACTED_SECRET]', line)
