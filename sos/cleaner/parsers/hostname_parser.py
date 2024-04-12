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
from sos.cleaner.mappings.hostname_map import SoSHostnameMap


class SoSHostnameParser(SoSCleanerParser):

    name = 'Hostname Parser'
    map_file_key = 'hostname_map'
    regex_patterns = [
        r'(((\b|_)[a-zA-Z0-9-\.]{1,200}\.[a-zA-Z]{1,63}(\b|_)))'
    ]

    def __init__(self, config, skip_clean_files=[]):
        self.mapping = SoSHostnameMap()
        super().__init__(config, skip_clean_files)

    def parse_line(self, line):
        """This will be called for every line in every file we process, so that
        every parser has a chance to scrub everything.

        We are overriding parent method since we need to swap ordering of
        _parse_line_with_compiled_regexes and _parse_line calls.
        """
        count = 0
        for skip_pattern in self.skip_line_patterns:
            if re.match(skip_pattern, line, re.I):
                return line, count
        line, _count = self._parse_line(line)
        count += _count
        if self.compile_regexes:
            line, _rcount = self._parse_line_with_compiled_regexes(line)
            count += _rcount
        return line, count
