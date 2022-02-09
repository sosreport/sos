# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.keyword_map import SoSKeywordMap


class SoSKeywordParser(SoSCleanerParser):
    """Handles parsing for user provided keywords
    """

    name = 'Keyword Parser'
    map_file_key = 'keyword_map'

    def __init__(self, config, keywords=None, keyword_file=None):
        self.mapping = SoSKeywordMap()
        self.user_keywords = []
        super(SoSKeywordParser, self).__init__(config)
        for _keyword in self.mapping.dataset.keys():
            self.user_keywords.append(_keyword)
        if keywords:
            for keyword in keywords:
                if keyword not in self.user_keywords:
                    # pre-generate an obfuscation mapping for each keyword
                    # this is necessary for cases where filenames are being
                    # obfuscated before or instead of file content
                    self.mapping.get(keyword.lower())
                    self.user_keywords.append(keyword)
        if keyword_file and os.path.exists(keyword_file):
            with open(keyword_file, 'r') as kwf:
                self.user_keywords.extend(kwf.read().splitlines())

    def _parse_line(self, line):
        return line, 0
