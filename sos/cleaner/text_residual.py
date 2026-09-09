# This file is part of the sos project: https://github.com/sosreport/sos
#
# See the LICENSE file in the source distribution for license information.

"""Read-only residual privacy checks for completed clean-text staging files.

These detectors are independent of the sanitizers. They neither invoke a
parser nor discover/map identities. IPv4 aliases must be supplied from this
invocation's generated mapping values, not accepted by address range. IPv6
and MAC reserved formats and intentional preservation rules follow existing
cleaner policy. Only a boolean verdict leaves the scanner.
"""

import re
import socket


_EMAIL = re.compile(r"[\w.!#$%&'*+/?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+")
_EMAIL_ALIAS = re.compile(
    r'(?:user|host|obfuscateduser)\d+@obfuscateddomain\d+\.'
    r'(?:example|host\d+|obfuscateduser\d+)', re.I
)
_AWS = re.compile(r'(?<![A-Za-z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}'
                  r'(?![A-Za-z0-9])')
_BEARER = re.compile(r'\bBearer[ \t]+(\S+)', re.I)
_JWT = re.compile(r'(?<![\w-])eyJ[\w-]+\.[\w-]+\.[\w-]+(?![\w-])')
_PRIVATE_KEY = re.compile(r'-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----')
_ASSIGNMENT = re.compile(
    r'''(?<![\w./-])(?:--)?["']?(?:[a-z0-9]+[_-])*'''
    r'(?:password|passwd|pwd|token|secret|api_key|api-key|apikey)'
    r'''["']?[ \t]*[=:][ \t]*(?P<quote>["']?)''', re.I
)
_USERNAME_CONTEXT = re.compile(
    r'''(?<![A-Za-z0-9_])(?P<key>acct|AUID|UID|user|ruser|USER|LOGNAME)'''
    r'''[ \t]*=[ \t]*["']?(?P<value>[A-Za-z_][A-Za-z0-9_.-]*)'''
    r'''(?=["'\s,;)]|$)|'''
    r'''\bfor[ \t]+(?P<sshd>[A-Za-z_][A-Za-z0-9_.-]*)'''
    r'''(?=[ \t]+(?:from|port)\b)|'''
    r'''\bfor[ \t]+user[ \t]+(?P<pam>[A-Za-z_][A-Za-z0-9_.-]*)'''
    r'''(?=[(\s]|$)|'''
    r'''(?m:^sudo:\s*(?P<sudo>[A-Za-z_][A-Za-z0-9_.-]*)\s*:)''')
_USERNAME_ALIAS = re.compile(r'obfuscateduser\d+$', re.I)
_PRESERVED_USERNAME = frozenset(('root', 'unset', 'nobody'))
_MARKER = re.compile(
    r'\[REDACTED_(?:SECRET|TOKEN|PRIVATE_KEY)\]'
    r'''(?=$|[\s"',;&}\])<>])'''
)
_IPV4 = re.compile(
    r'(?<![0-9.-])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9.])'
)
# Validate whole colon tokens with inet_pton; this excludes SELinux contexts
# and avoids treating an IPv6 substring or a UUID as a MAC address.
_IPV6 = re.compile(r'(?<![\w:.-])[a-f0-9:]*:[a-f0-9:.]+(?![\w:.-])',
                   re.I)
_MAC = re.compile(
    r'(?<![\w:.-])(?:'
    r'(?:[a-f0-9]{2}[:_-]){5}[a-f0-9]{2}|'
    r'(?:[a-f0-9]{2}[:-]){7}[a-f0-9]{2}|'
    r'(?:[a-f0-9]{4}[:-]){3}[a-f0-9]{4}'
    r')(?![\w:.-])', re.I
)


def _packed(value, family):
    """Validate without an exception message containing the candidate."""
    try:
        return socket.inet_pton(family, value.split('/', 1)[0])
    except OSError:
        return None


def _mac_allowed(value):
    value = value.lower().replace('-', ':').replace('_', ':')
    return (value in ('00:00:00:00:00:00', 'ff:ff:ff:ff:ff:ff')
            or value.startswith(('53:4f:53:', '534f:53')))


def _ipv4_preserved(address):
    # Existing cleaner deliberately retains these special/public addresses.
    return (address[0] in (0, 1, 127, 255)
            or address[:2] == b'\xa9\xfe'
            or address in (b'\x08\x08\x08\x08', b'\x08\x08\x04\x04'))


def _ipv6_preserved(value, address):
    # Unspecified/loopback, reserved aliases, and link-local network prefixes.
    if address in (bytes(16), bytes(15) + b'\x01'):
        return True
    if address[0] == 0x53 or address[:2] == b'\xfd\x53':
        return True
    if address[:8] == b'\xfe\x80' + bytes(6):
        if address[8:] == bytes(8):
            return True
        # MAC parsing can replace an EUI suffix after IPv6 obfuscation.
        if address[8:13] == b'\x53\x4f\x53\xff\xfe':
            return True
    return _mac_allowed(value)


def _has_residual(line, ipv4_aliases, ipv6_aliases):
    if _AWS.search(line) or _JWT.search(line) or _PRIVATE_KEY.search(line):
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
                      ('value', 'sshd', 'pam', 'sudo')
                      if match.group(name)), '')
        if (value and value.lower() not in _PRESERVED_USERNAME
                and not _USERNAME_ALIAS.fullmatch(value)):
            return True
    # Match dnf's intentionally preserved journal version lines, as the IP
    # parser does. Package names such as package-2.3.4.5 do not match _IPV4.
    if not re.search(r'dnf\[.*\]:', line, re.I):
        for match in _IPV4.finditer(line):
            address = _packed(match[0], socket.AF_INET)
            if (address is not None and address not in ipv4_aliases
                    and not _ipv4_preserved(address)):
                return True
    for match in _IPV6.finditer(line):
        address = _packed(match[0], socket.AF_INET6)
        if (address is not None and address not in ipv6_aliases
                and not _ipv6_preserved(match[0], address)):
            return True
    for match in _MAC.finditer(line):
        if not _mac_allowed(match[0]):
            return True
    return False


def check_staged_output(staged, ipv4_aliases=(), ipv6_aliases=()):
    """Scan UTF-8 staging line by line, restoring its original byte position.

    Memory for input is limited to one line, like sanitize_stream. Supplied
    aliases must be generated values only, excluding identity/failure entries.
    Scanner/read/seek/decode errors also fail closed without exposing values.
    """
    try:
        position = staged.tell()
    except Exception:
        return False
    passed = False
    try:
        ipv4 = {_packed(value, socket.AF_INET) for value in ipv4_aliases}
        ipv6 = {_packed(value, socket.AF_INET6) for value in ipv6_aliases}
        staged.seek(0)
        passed = True
        for raw_line in staged:
            if _has_residual(raw_line.decode('utf-8'), ipv4, ipv6):
                passed = False
                break
    except Exception:
        passed = False
    try:
        staged.seek(position)
    except Exception:
        passed = False
    return passed
