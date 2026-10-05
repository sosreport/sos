import re
import socket
import unittest

from sos.cleaner.report_residual import (
    ResidualMatcher, build_manifest_patterns)
from sos.cleaner.text_residual import (
    _ASSIGNMENT, _AWS, _BEARER, _EMAIL, _EMAIL_ALIAS, _IPV4, _IPV6, _JWT,
    _MAC, _MARKER, _PRIVATE_KEY, _PRESERVED_USERNAME, _USERNAME_CONTEXT,
    _has_residual, _ipv4_preserved, _ipv6_preserved, _packed)


def reference_category(text, patterns):
    best = None
    order = 0
    for namespace, values in patterns.items():
        for _original, pattern in values:
            match = pattern.search(text)
            if match is not None:
                candidate = (match.start(), order, namespace)
                if best is None or candidate[:2] < best[:2]:
                    best = candidate
            order += 1
    return best[2] if best is not None else None


def reference_has_residual(line, ipv4_aliases, ipv6_aliases):
    if (_AWS.search(line) or _JWT.search(line) or
            _PRIVATE_KEY.search(line)):
        return True
    for match in _EMAIL.finditer(line):
        if not _EMAIL_ALIAS.fullmatch(match[0].rstrip('.')):
            return True
    for match in _BEARER.finditer(line):
        if not _MARKER.match(match[1]):
            return True
    for match in _ASSIGNMENT.finditer(line):
        marker = _MARKER.match(line, match.end())
        if not marker:
            return True
        if match['quote']:
            tail = line[marker.end():]
            if tail and not tail.startswith(match['quote']) and tail.strip():
                return True
    for match in _USERNAME_CONTEXT.finditer(line):
        value = next((match.group(name) for name in
                      ('value', 'sshd', 'pam', 'sudo') if match.group(name)),
                     '')
        if (value and value.lower() not in _PRESERVED_USERNAME and
                not re.fullmatch(r'obfuscateduser\d+$', value, re.I)):
            return True
    if not re.search(r'dnf\[.*\]:', line, re.I):
        for match in _IPV4.finditer(line):
            address = _packed(match[0], socket.AF_INET)
            if (address is not None and address not in ipv4_aliases and
                    not _ipv4_preserved(address)):
                return True
    for match in _IPV6.finditer(line):
        address = _packed(match[0], socket.AF_INET6)
        if (address is not None and address not in ipv6_aliases and
                not _ipv6_preserved(match[0], address)):
            return True
    for match in _MAC.finditer(line):
        value = match[0].lower().replace('-', ':').replace('_', ':')
        if not (value in ('00:00:00:00:00:00', 'ff:ff:ff:ff:ff:ff') or
                value.startswith(('53:4f:53:', '534f:53'))):
            return True
    return False


class Phase29ResidualTests(unittest.TestCase):
    def setUp(self):
        self.mappings = {
            'hostnames': {'node.example': 'host0.example'},
            'domains': {'customer.example': 'domain0.example'},
            'ipv4': {'198.51.100.42': '100.0.0.1'},
            'ipv6': {'2001:db8::42': '534f::42'},
            'mac': {'aa:bb:cc:dd:ee:ff': '53:4f:53:00:00:01'},
            'emails': {'alice@customer.example': 'user0@domain0.example'},
            'usernames': {'alice': 'obfuscateduser0'},
        }
        self.matcher = ResidualMatcher(self.mappings)
        self.patterns = build_manifest_patterns(self.mappings)
        self.lines = (
            '', 'ordinary diagnostic text',
            'node.example customer.example alice',
            '198.51.100.42 2001:db8::42 aa:bb:cc:dd:ee:ff',
            'local=198.51.100.42/54321_tcp remote=203.0.113.7/31001_tcp',
            'alice@customer.example', 'acct="alice"',
            'Authorization: Bearer unresolved',
            '-----BEGIN PRIVATE KEY-----', 'AKIAABCDEFGHIJKLMNOP',
            'eyJheader.payload.signature', 'password=secret',
            'overlap node.example.example', 'near 198.51.100.4',
            'unicode café Ω', 'x' * 200000,
            'netstat [::ffff:198.51.100.42]:443',
            'State=Connected pending=[r---]',
        )

    def test_known_original_matcher_matches_reference(self):
        for line in self.lines:
            with self.subTest(line_length=len(line)):
                self.assertEqual(
                    self.matcher.match_category(line),
                    reference_category(line, self.patterns))

    def test_generic_detectors_match_reference(self):
        ipv4 = {_packed('100.0.0.1', socket.AF_INET)}
        ipv6 = {_packed('534f::42', socket.AF_INET6)}
        for line in self.lines:
            with self.subTest(line_length=len(line)):
                self.assertEqual(
                    _has_residual(line, ipv4, ipv6),
                    reference_has_residual(line, ipv4, ipv6))
