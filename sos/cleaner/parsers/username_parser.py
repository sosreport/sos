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
    skip_list = [
        'core',
        'nobody',
        'nfsnobody',
        'shutdown',
        'stack',
        'reboot',
        'root',
        'ubuntu',
        'username',
        'wtmp'
    ]

    def __init__(self, config, opt_names=None):
        self.mapping = SoSUsernameMap()
        super(SoSUsernameParser, self).__init__(config)
        self.mapping.load_names_from_options(opt_names)

    def load_usernames_into_map(self, content):
        """Since we don't get the list of usernames from a straight regex for
        this parser, we need to override the initial parser prepping here.
        """
        users = set()
        for line in content.splitlines():
            try:
                user = line.split()[0]
            except Exception:
                continue
            if not user or user.lower() in self.skip_list:
                continue
            users.add(user)
        for each in users:
            self.mapping.get(each)

    def _parse_line(self, line):
        return line, 0
