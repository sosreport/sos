# This file is part of the sos project: https://github.com/sosreport/sos

"""Invocation-local sanitization state.

This module deliberately does not participate in legacy archive cleaning.
Its map classes reuse the legacy algorithms while replacing their persistent
cache boundary with an in-memory boundary and making mutable state local to
one session.
"""

import re

from sos.cleaner.mappings.hostname_map import SoSHostnameMap
from sos.cleaner.mappings import SoSMap
from sos.cleaner.mappings.ip_map import SoSIPMap
from sos.cleaner.mappings.ipv6_map import (SoSIPv6Map,
                                           ObfuscatedIPv6Network)
from sos.cleaner.mappings.mac_map import SoSMacMap
from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.parsers.hostname_parser import SoSHostnameParser
from sos.cleaner.parsers.ip_parser import SoSIPParser
from sos.cleaner.parsers.ipv6_parser import SoSIPv6Parser
from sos.cleaner.parsers.mac_parser import SoSMacParser
from sos.cleaner.text_identity import TextEmailParser, TextUsernameParser
from sos.cleaner.text_secrets import SecretRedactor


class SessionStageError(Exception):
    """A parser-stage failure without including input contents."""

    def __init__(self, name, secret=False):
        self.name = name
        self.secret = secret
        super().__init__(name)


class _SessionMap:
    """Mixin that gives SoSMap subclasses an in-memory add operation."""

    def load_entries(self):
        # Keep the existing clean-text temporary-directory contract. This
        # creates only empty, private staging directories; SessionMap.add()
        # never writes mapping entries or reads an existing cache.
        SoSMap.load_entries(self)

    def add(self, item):
        if self.ignore_item(item):
            return item
        if item not in self.dataset:
            self.add_sanitised_item_to_dataset(item)
        return self.dataset[item]


class SessionHostnameMap(_SessionMap, SoSHostnameMap):
    def __init__(self, workdir, static_regex):
        self.host_count = 0
        self.domain_count = 0
        self._domains = {}
        self.hosts = {}
        super().__init__(workdir, static_regex)


class SessionIPMap(_SessionMap, SoSIPMap):
    def __init__(self, workdir, static_regex):
        self._networks = {}
        self.obfuscated_ips = set()
        self.network_first_octet = 100
        self._saddr_cnt = 2886795264
        super().__init__(workdir, static_regex)


class SessionIPv6Network(ObfuscatedIPv6Network):
    def __init__(self, addr, obfuscation='', used_hexes=None, counters=None):
        self.ob_counters = counters if counters is not None else {}
        super().__init__(addr, obfuscation, used_hexes)


class SessionIPv6Map(_SessionMap, SoSIPv6Map):
    def __init__(self, workdir, static_regex):
        self.networks = {}
        self.first_hexes = ['534f']
        self._ob_counters = {}
        super().__init__(workdir, static_regex)

    def _get_network(self, address, obfuscated=''):
        key = address.compressed
        if key not in self.networks:
            self.networks[key] = SessionIPv6Network(
                address, obfuscated, self.first_hexes, self._ob_counters)
        return self.networks[key]


class SessionMacMap(_SessionMap, SoSMacMap):
    def __init__(self, workdir, static_regex):
        self.ob_hextets_cnt = 0
        super().__init__(workdir, static_regex)


class SessionHostnameParser(SoSHostnameParser):
    def __init__(self, workdir):
        self.mapping = SessionHostnameMap(workdir, self.regex_pattern)
        SoSCleanerParser.__init__(self, {})


class SessionIPParser(SoSIPParser):
    def __init__(self, workdir):
        self.mapping = SessionIPMap(workdir, self.regex_pattern)
        SoSCleanerParser.__init__(self, {})


class SessionIPv6Parser(SoSIPv6Parser):
    def __init__(self, workdir):
        self.mapping = SessionIPv6Map(workdir, self.regex_pattern)
        SoSCleanerParser.__init__(self, {})


class SessionMacParser(SoSMacParser):
    def __init__(self, workdir):
        self.mapping = SessionMacMap(workdir, self.regex_pattern)
        SoSCleanerParser.__init__(self, {})


class SessionUsernameParser(TextUsernameParser):
    """Text username parser using the existing text-only policy."""

    pass


class SanitizationSession:
    """One invocation's identity mappings and secret-redaction state."""

    def __init__(self, workdir, hostnames=(), domains=(), usernames=(),
                 redactor=None):
        self.redactor = redactor if redactor is not None else SecretRedactor()
        self.email_parser = TextEmailParser()
        self.username_parser = SessionUsernameParser(workdir, usernames)
        self.hostname_parser = SessionHostnameParser(workdir)
        self.ip_parser = SessionIPParser(workdir)
        self.ipv6_parser = SessionIPv6Parser(workdir)
        self.mac_parser = SessionMacParser(workdir)
        self.parsers = [
            self.email_parser, self.username_parser, self.hostname_parser,
            self.ip_parser, self.ipv6_parser, self.mac_parser
        ]
        self.explicit_domains = {
            domain.lower().rstrip('.') for domain in domains
        }
        for identity in tuple(hostnames) + tuple(domains):
            self.hostname_parser.mapping.add(identity.lower())
        self.hostname_parser.generate_item_regexes()

        self.mappings = {
            'hostname': self.hostname_parser.mapping,
            'domain': self.hostname_parser.mapping,
            'ipv4': self.ip_parser.mapping,
            'ipv6': self.ipv6_parser.mapping,
            'mac': self.mac_parser.mapping,
            'email': self.email_parser,
            'username': self.username_parser.mapping,
        }

    def sanitize_line(self, line):
        try:
            line = self.redactor.redact(line)
        except Exception:
            raise SessionStageError('secret', secret=True) from None
        for parser in self.parsers:
            try:
                line, _ = parser.parse_line(line)
            except Exception:
                raise SessionStageError(parser.name) from None
        return line

    def aliases(self, namespace):
        mapping = self.mappings[namespace]
        if namespace == 'email':
            return list(mapping._addresses.values())
        return [value for original, value in mapping.dataset.items()
                if original != value]

    def add_hostname(self, value):
        """Add a discovered hostname/domain without processing text."""
        return self.hostname_parser.mapping.add(value.lower().rstrip('.'))

    def add_ip(self, value):
        """Add a discovered IPv4 address or network."""
        return self.ip_parser.mapping.add(value)

    def add_ipv6(self, value):
        """Add a discovered IPv6 address or network."""
        return self.ipv6_parser.mapping.add(value)

    def add_mac(self, value):
        """Add a discovered MAC address."""
        return self.mac_parser.mapping.add(value)

    def add_username(self, value):
        """Add a discovered contextual username."""
        if re.fullmatch(r'obfuscateduser\d+', value, re.I):
            return value
        return self.username_parser.mapping.add(value)

    def add_email(self, value):
        """Register an email address in the email namespace."""
        self.email_parser.parse_line(value)

    def summary(self):
        """Return mapping counts only; never return identity values."""
        return {
            'hostnames': len(self.hostname_parser.mapping.hosts),
            'ipv4': len(self.ip_parser.mapping.dataset),
            'ipv6': len(self.ipv6_parser.mapping.dataset),
            'mac': len(self.mac_parser.mapping.dataset),
            'usernames': len(self.username_parser.mapping.dataset),
            'emails': len(self.email_parser._addresses),
        }
