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
    preserved_identities = frozenset(('root', 'unset', 'nobody'))

    def __init__(self, workdir, usernames):
        self._seeds = set(usernames)
        # Text-only maps are invocation-local. Keep the legacy map untouched.
        self.name_count = 0
        super().__init__(workdir)

    def sanitize_item(self, item):
        replacement = super().sanitize_item(item)
        while replacement in self._seeds:
            replacement = super().sanitize_item(item)
        return replacement

    def load_entries(self):
        pass

    def add(self, item):
        if item.lower() in self.preserved_identities:
            return item
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

    # These fields are authentication/audit grammar, rather than guesses from
    # ordinary words. Values are deliberately limited to textual account
    # identifiers and stop at the surrounding log punctuation.
    _context = re.compile(
        r'''(?<![A-Za-z0-9_])(?P<key>acct|AUID|UID|user|ruser|USER|LOGNAME)'''
        r'''[ \t]*=[ \t]*["']?(?P<value>[A-Za-z_][A-Za-z0-9_.-]*)'''
        r'''(?=["'\s,;)]|$)''')
    _sshd_for = re.compile(
        r'\bfor[ \t]+(?P<value>[A-Za-z_][A-Za-z0-9_.-]*)'
        r'(?=[ \t]+(?:from|port)\b)')
    _pam_user = re.compile(
        r'\bfor[ \t]+user[ \t]+(?P<value>[A-Za-z_][A-Za-z0-9_.-]*)'
        r'(?=[(\s]|$)')
    _sudo_user = re.compile(
        r'(?m)^sudo:\s*(?P<value>[A-Za-z_][A-Za-z0-9_.-]*)\s*:' )

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

    def parse_line(self, line):
        line, count = self._parse_line_with_compiled_regexes(line)
        for pattern in (self._context, self._sshd_for, self._pam_user,
                        self._sudo_user):
            def replace(match):
                if re.fullmatch(r'obfuscateduser\d+',
                                match.group('value'), re.I):
                    return match.group(0)
                return match.group(0).replace(
                    match.group('value'), self.mapping.add(match.group('value')),
                    1)
            line, found = pattern.subn(replace, line)
            count += found
        return line, count


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
            if re.fullmatch(r'user\d+@obfuscateddomain\d+\.example',
                            match[0], re.I):
                return match[0]
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
