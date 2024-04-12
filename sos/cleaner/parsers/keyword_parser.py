# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.keyword_map import SoSKeywordMap


class SoSKeywordParser(SoSCleanerParser):
    """Handles parsing for user provided keywords
    """

    name = 'Keyword Parser'
    map_file_key = 'keyword_map'

    def __init__(self, config, skip_clean_files=[]):
        self.mapping = SoSKeywordMap()
        super().__init__(config, skip_clean_files)

    def _parse_line(self, line):
        return line, 0
