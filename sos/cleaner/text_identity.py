# This file is part of the sos project: https://github.com/sosreport/sos
#
# See the LICENSE file in the source distribution for license information.

"""Invocation-local identity handling for clean-text, without disk caches."""

import re

from sos.cleaner.mappings.username_map import SoSUsernameMap
from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.parsers.username_parser import SoSUsernameParser


class TextUsernameMap(SoSUsernameMap):
    """Reuse username pseudonyms with exact, case-sensitive token matching.

    Dots, hyphens and underscores belong to usernames, so a seed such as
    'user' cannot alter 'user-123.slice'. Explicit short names are supported.
    Raw seeds stay in memory; the archive mapping remains unchanged.
    """

    ignore_short_items = False
    use_token_lookup = False

    def __init__(self, workdir, usernames):
        self._seeds = set(usernames)
        super().__init__(workdir)

    def sanitize_item(self, item):
        replacement = super().sanitize_item(item)
        while replacement in self._seeds:
            replacement = super().sanitize_item(item)
        return replacement

    def load_entries(self):
        pass

    def add(self, item):
        if item and item not in self.dataset:
            self.dataset[item] = self.sanitize_item(item)
            self.add_regex_item(item)
        return self.dataset.get(item, item)

    def add_regex_item(self, item):
        self._regexes_made.add(item)
        if not self.initializing:
            self.generate_compiled_regexes()

    def generate_compiled_regexes(self, only_search=False):
        self.compiled_regexes = [
            (item, re.compile(r'(?<![\w.-])' + re.escape(item)
                              + r'(?![\w.-])'))
            for item in sorted(self._regexes_made, key=len, reverse=True)
        ]
        self.compiled_search = re.compile(
            '|'.join(reg.pattern for _, reg in self.compiled_regexes)
            or r'(?!)'
        )


class TextUsernameParser(SoSUsernameParser):
    """Use the existing username parser with a text-only mapping policy."""

    def __init__(self, workdir, usernames):
        self.mapping = TextUsernameMap(workdir, usernames)
        SoSCleanerParser.__init__(self, {})
        for username in usernames:
            self.mapping.add(username)
        self.generate_item_regexes()

    def _parse_line_with_compiled_regexes(self, line):
        # One substitution pass prevents a generated name matching a seed.
        return self.mapping.compiled_search.subn(
            lambda match: self.mapping.get(match[0]), line
        )


class TextEmailParser:
    """Recognize ordinary ASCII dot-atom emails in prose/configuration.

    Case variants of the whole address share a pseudonym. Domains also share
    a pseudonym across different mailboxes. No email-derived identity is
    seeded into the hostname or username parsers, or written to disk.
    """

    name = 'Email Parser'
    # Exclude slash and equals to preserve common path/assignment prefixes.
    _atom = r"[a-z0-9!#$%&'*+?^_`{|}~-]+"
    _label = r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
    _email = re.compile(
        r"(?<![\w.!#$%&'*+?^_`{|}~-])"
        + _atom + r'(?:\.' + _atom + r')*@'
        + _label + r'(?:\.' + _label + r')*\.[a-z]{2,63}'
        + r'(?![\w@-])', re.I
    )

    def __init__(self):
        self._addresses = {}
        self._domains = {}

    def parse_line(self, line):
        def replace(match):
            address = match[0].lower()
            if address not in self._addresses:
                domain = address.rsplit('@', 1)[1]
                if domain not in self._domains:
                    self._domains[domain] = (
                        f'obfuscateddomain{len(self._domains)}.example'
                    )
                self._addresses[address] = (
                    f'user{len(self._addresses)}@{self._domains[domain]}'
                )
            return self._addresses[address]

        return self._email.subn(replace, line)
