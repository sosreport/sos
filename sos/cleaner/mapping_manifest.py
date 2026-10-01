# This file is part of the sos project: https://github.com/sosreport/sos

"""Private, in-memory identity correlations for one sanitizer invocation."""

import copy
import re


class SoSMappingManifest:
    """A versioned, private view of a :class:`SanitizationSession`.

    Construction snapshots only original-to-pseudonym pairs. It deliberately
    does not retain the session, parser objects, redactor, counters, or cache
    paths. Raw mappings are available only through the explicit ``raw_mappings``
    method; ``summary`` is the safe default interface.
    """

    schema_version = 1
    namespaces = (
        'hostnames', 'domains', 'ipv4', 'ipv6', 'mac', 'emails', 'usernames'
    )
    _generated_username = re.compile(r'obfuscateduser\d+$', re.I)
    _generated_email = re.compile(
        r'user\d+@obfuscateddomain\d+\.example$', re.I)

    def __init__(self, mappings):
        self._mappings = {
            namespace: dict(mappings.get(namespace, {}))
            for namespace in self.namespaces
        }

    @classmethod
    def from_session(cls, session):
        """Snapshot safe identity mappings from one session."""
        hostname_map = session.hostname_parser.mapping
        hostname_values = set(hostname_map.dataset.values())
        hostnames = {
            original: alias
            for original, alias in hostname_map.hosts.items()
            if original != alias and original not in hostname_values
        }
        domains = {}
        fqdn_hostnames = {}
        for original, alias in hostname_map.dataset.items():
            if original == alias or original in hostname_values:
                continue
            parts = original.split('.')
            if len(parts) < 2:
                continue
            stem = '.'.join(parts[:-1]).lower()
            if stem in hostname_map._domains:
                domains[original] = alias
                continue
            domain_stem = '.'.join(parts[1:-1]).lower()
            host_alias = hostname_map.hosts.get(parts[0].lower())
            if host_alias and domain_stem in hostname_map._domains:
                fqdn_hostnames[original] = f'{host_alias}.{alias}'
        hostnames.update(fqdn_hostnames)

        return cls({
            'hostnames': hostnames,
            'domains': domains,
            'ipv4': cls._map_dataset(session.ip_parser.mapping),
            'ipv6': cls._map_dataset(session.ipv6_parser.mapping),
            'mac': cls._map_dataset(session.mac_parser.mapping),
            'emails': cls._email_mappings(session.email_parser),
            'usernames': cls._username_mappings(
                session.username_parser.mapping),
        })

    @staticmethod
    def _map_dataset(mapping):
        aliases = set(mapping.dataset.values())
        return {
            original: alias for original, alias in mapping.dataset.items()
            if original != alias and original not in aliases
        }

    @classmethod
    def _username_mappings(cls, mapping):
        aliases = set(mapping.dataset.values())
        return {
            original: alias for original, alias in mapping.dataset.items()
            if original != alias and original not in aliases
            and not cls._generated_username.fullmatch(original)
        }

    @classmethod
    def _email_mappings(cls, parser):
        aliases = set(parser._addresses.values())
        return {
            original: alias for original, alias in parser._addresses.items()
            if original != alias and original not in aliases
            and not cls._generated_email.fullmatch(original)
        }

    def summary(self):
        """Return counts only."""
        return {namespace: len(self._mappings[namespace])
                for namespace in self.namespaces}

    def raw_mappings(self):
        """Explicitly return a detached, serializable raw manifest model."""
        return copy.deepcopy({
            'schema_version': self.schema_version,
            **self._mappings,
        })
