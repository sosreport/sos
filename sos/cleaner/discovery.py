# This file is part of the sos project: https://github.com/sosreport/sos

"""High-confidence identity discovery from an extracted sosreport tree."""

import glob
import ipaddress
import os
import re

from sos.cleaner.session import SanitizationSession
from sos.cleaner.text_identity import TextUsernameParser
from sos.cleaner.text_secrets import SecretRedactor


class ReportIdentityDiscovery:
    """Populate a session from a fixed, structured set of report sources."""

    _hostname_files = (
        'hostname',
        'etc/hostname',
        'sos_commands/host/hostname_-f',
        'data/insights_commands/hostname_-f',
    )
    _hosts_file = 'etc/hosts'
    _address_files = (
        'sos_commands/networking/ip_-o_addr',
        'sos_commands/networking/ip_addr',
        'sos_commands/networking/ip_-d_address',
        'data/insights_commands/ip_addr',
        'data/insights_commands/ip_-o_addr',
    )
    _route_files = (
        'sos_commands/networking/ip_route',
        'sos_commands/networking/ip_-6_route',
        'sos_commands/networking/ip_route_show',
        'sos_commands/networking/ip_-6_route_show',
    )
    _auth_globs = (
        'var/log/audit/audit.log*',
        'var/log/secure*',
        'var/log/auth.log*',
    )
    _nm_globs = (
        'etc/NetworkManager/system-connections/*.nmconnection',
        'etc/NetworkManager/system-connections/*',
    )

    _ipv4 = re.compile(
        r'(?<![0-9.])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/\d{1,2})?'
        r'(?![0-9.])')
    _ipv6 = re.compile(
        r'(?<![\w:.-])(?:[0-9a-f]{1,4}:){1,7}[0-9a-f:.]*'
        r'(?:/\d{1,3})?(?![\w:.-])', re.I)
    _mac = re.compile(
        r'(?<![\w:.-])(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}'
        r'(?![\w:.-])', re.I)
    _email = re.compile(
        r"(?<![\w.!#$%&'*+?^_`{|}~-])"
        r"[a-z0-9!#$%&'*+?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+?^_`{|}~-]+)*@"
        r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
        r'(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+', re.I)
    _nm_key = re.compile(
        r'^(?:address1|addresses|gateway|gateway4|gateway6|dns|dns-search)'
        r'\s*[=:]', re.I)

    def __init__(self, root, session):
        self.root = os.path.abspath(root)
        self.session = session
        self._seen = set()

    def discover(self):
        """Discover identities, returning a counts-only summary."""
        self._discover_hostname_files()
        self._discover_hosts()
        self._discover_address_files()
        self._discover_route_files()
        self._discover_nm_profiles()
        self._discover_authentication()
        return self.summary()

    def summary(self):
        """Return counts only, with no raw identity values."""
        return self.session.summary()

    def _read(self, relative):
        path = os.path.join(self.root, relative)
        try:
            if not os.path.isfile(path):
                return None
            with open(path, 'r', encoding='utf-8', errors='replace') as stream:
                return stream.read()
        except (OSError, UnicodeError):
            return None

    def _add_hostname_candidate(self, value):
        value = value.strip().strip('"\'').rstrip('.')
        if not value or value.lower() in ('localhost', 'localhost.localdomain'):
            return
        if any(char not in 'abcdefghijklmnopqrstuvwxyz'
               'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_' for char in value):
            return
        try:
            ipaddress.ip_address(value)
            return
        except ValueError:
            pass
        parts = value.split('.')
        if any(not part or len(part) > 63 for part in parts):
            return
        if len(parts) == 1:
            self._safe_add(self.session.add_hostname, value)
            return
        domain = '.'.join(parts[1:]).lower()
        if domain in self.session.explicit_domains or any(
                domain.endswith('.' + candidate)
                for candidate in self.session.explicit_domains):
            self._safe_add(self.session.add_hostname, value)
            return
        # A structured hostname source can safely provide its short name,
        # while an unrelated FQDN must not seed a domain implicitly.
        if len(parts[0]) > 2:
            self._safe_add(self.session.add_hostname, parts[0])

    @staticmethod
    def _safe_add(function, value):
        """Ignore malformed candidates without exposing them diagnostically."""
        try:
            function(value)
        except Exception:
            pass

    def _discover_hostname_files(self):
        for relative in self._hostname_files:
            content = self._read(relative)
            if content is None:
                continue
            value = content.strip().splitlines()[0] if content.strip() else ''
            self._add_hostname_candidate(value)

    def _discover_hosts(self):
        content = self._read(self._hosts_file)
        if content is None:
            return
        for line in content.splitlines():
            line = line.split('#', 1)[0].strip()
            fields = line.split()
            if len(fields) < 2:
                continue
            try:
                ipaddress.ip_address(fields[0])
            except ValueError:
                continue
            for value in fields[1:]:
                self._add_hostname_candidate(value)
                if '.' not in value:
                    continue

    @staticmethod
    def _valid_ip(value, family):
        try:
            raw = value.split('/', 1)[0]
            address = ipaddress.ip_address(raw)
            return address if address.version == family else None
        except ValueError:
            return None

    def _discover_ips_from_line(self, line, include_mac=True):
        for match in self._ipv4.findall(line):
            if self._valid_ip(match, 4):
                self._safe_add(self.session.add_ip, match)
        for match in self._ipv6.findall(line):
            if self._valid_ip(match, 6):
                self._safe_add(self.session.add_ipv6, match)
        if include_mac:
            for match in self._mac.findall(line):
                self._safe_add(self.session.add_mac, match)

    def _discover_address_files(self):
        for relative in self._address_files:
            content = self._read(relative)
            if content is None:
                continue
            for line in content.splitlines():
                self._discover_ips_from_line(line)

    def _discover_route_files(self):
        for relative in self._route_files:
            content = self._read(relative)
            if content is None:
                continue
            for line in content.splitlines():
                self._discover_ips_from_line(line, include_mac=False)

    def _discover_nm_profiles(self):
        paths = set()
        for pattern in self._nm_globs:
            paths.update(glob.glob(os.path.join(self.root, pattern)))
        for path in sorted(paths):
            if not os.path.isfile(path):
                continue
            relative = os.path.relpath(path, self.root)
            content = self._read(relative)
            if content is None:
                continue
            for line in content.splitlines():
                if self._nm_key.match(line.strip()):
                    self._discover_ips_from_line(line, include_mac=False)

    def _discover_authentication(self):
        paths = set()
        for pattern in self._auth_globs:
            paths.update(glob.glob(os.path.join(self.root, pattern)))
        username_patterns = (TextUsernameParser._context,
                             TextUsernameParser._sshd_for,
                             TextUsernameParser._pam_user,
                             TextUsernameParser._sudo_user)
        for path in sorted(paths):
            if not os.path.isfile(path):
                continue
            relative = os.path.relpath(path, self.root)
            content = self._read(relative)
            if content is None:
                continue
            redactor = SecretRedactor()
            for raw_line in content.splitlines():
                line = redactor.redact(raw_line)
                for pattern in username_patterns:
                    for match in pattern.finditer(line):
                        value = match.groupdict().get('value')
                        if value:
                            self._safe_add(self.session.add_username, value)
                for match in self._email.finditer(line):
                    self._safe_add(self.session.add_email, match[0])
