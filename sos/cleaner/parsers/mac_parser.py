# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re

from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.mac_map import SoSMacMap


# aa:bb:cc:fe:ff:dd:ee:ff
IPV6_REG_8HEX = (
    r'((?<!([0-9a-fA-F\'\"]:)|::)(?:[^:|-])?(?:[0-9a-fA-F]{2}(?::|-)){7}'
    r'[0-9a-fA-F]{2}(?:\'|\")?(?:\/|\,|\-|\.|\s|$))'
)
# aabb:ccee:ddee:ffaa
# - but disallow "substrings"
#   - but allow fe80: or fe80:: prefix for link-local
IPV6_REG_4HEX = (
    r'((?<!(?:([.|^|\b]{5}\w|[.|^|\b]fe80:|fe80::)))'
    r'(?:([0-9a-fA-F]{4}:){3}[0-9a-fA-F]{4})(?!\w))|'
    r'(?:(?<!\w)(([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{4})(?!\w))'
)
# aa:bb:cc:dd:ee:ff avoiding ipv6 substring matches
IPV4_REG = (
    r'((?<!([0-9a-fA-F\'\"]:)|::)'
    r'(?:([^:\-])?(?:([0-9a-fA-F]{2}([:\-\_])){5,6}(?:[0-9a-fA-F]{2}))))'
)


class SoSMacParser(SoSCleanerParser):
    """Handles parsing for MAC addresses"""

    name = 'MAC Parser'
    # Cheap pre-filter: any two hex pairs separated by : - or _
    # All MAC formats (6-byte, 8-byte, 4-hex-quad) contain this substring.
    # False positives are fine — the full regex rejects them.
    _quick_check = re.compile(r'[0-9a-fA-F]{2}[:\-_][0-9a-fA-F]{2}')
    regex_pattern = re.compile(
        rf'(({IPV6_REG_8HEX})|({IPV6_REG_4HEX})|({IPV4_REG}))'
    )
    obfuscated_patterns = (
        '53:4f:53',
        '534f:53'
    )
    parser_skip_files = [
        'sos_commands/.*/modinfo.*'
    ]
    map_file_key = 'mac_map'
    compile_regexes = False
    _contiguous_known = re.compile(
        r'(?<![A-Za-z0-9_.:-])(?P<value>[0-9a-fA-F]{12})'
        r'(?![A-Za-z0-9_.:-])')

    def __init__(self, config, workdir, skip_cleaning_files=[]):
        self.mapping = SoSMacMap(workdir, self.regex_pattern)
        super().__init__(config, skip_cleaning_files)

    def reduce_mac_match(self, match):
        """Strips away leading and trailing non-alphanum characters from any
        matched string to leave us with just the bare MAC addr
        """
        while not match[0] in '0123456789abcdefABCDEF':
            match = match[1:]
        while not match[-1] in '0123456789abcdefABCDEF':
            match = match[0:-1]
        # just to be safe, call strip() to remove any padding
        return match.strip()

    def _parse_line(self, line):
        count = 0
        if self._quick_check.search(line):
            matches = [m[0] for m in self.regex_pattern.findall(line)]
            if matches:
                count += len(matches)
                for match in matches:
                    stripped_match = self.reduce_mac_match(match)
                    if stripped_match.startswith(self.obfuscated_patterns):
                        # avoid double scrubbing
                        continue
                    new_match = self.mapping.get(stripped_match)
                    line = line.replace(stripped_match, new_match)
        # proc/net/dev_mcast emits known MACs as twelve contiguous hex digits.
        # Only replace values already present in the mapping: this path never
        # discovers arbitrary hexadecimal strings, especially while mappings
        # are frozen for report sanitization.
        known = {}
        for original, alias in self.mapping.dataset.items():
            normalized = re.sub(r'[^0-9a-f]', '', original.lower())
            if len(normalized) == 12:
                known[normalized] = alias
        def replace_contiguous(match):
            return known.get(match.group('value').lower(), match.group(0))
        line = self._contiguous_known.sub(replace_contiguous, line)
        return line, count
