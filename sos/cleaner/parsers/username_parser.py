# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.username_map import SoSUsernameMap


class SoSUsernameParser(SoSCleanerParser):
    """Parser for obfuscating usernames within an sosreport archive.

    Note that this parser does not rely on regex matching directly, like most
    other parsers do. Instead, usernames are discovered via scraping the
    collected output of lastlog. As such, we do not discover new usernames
    later on, and only usernames present in lastlog output will be obfuscated,
    and those passed via the --usernames option if one is provided.
    """

    name = 'Username Parser'
    map_file_key = 'username_map'
    regex_patterns = []

    def __init__(self, config, skip_clean_files=[]):
        self.mapping = SoSUsernameMap()
        super().__init__(config, skip_clean_files)

    def _parse_line(self, line):
        return line, 0
