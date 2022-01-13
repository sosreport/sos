# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re


class SoSCleanerParser():
    """Parsers are used to build objects that will take a line as input,
    parse it for a particular pattern (E.G. IP addresses) and then make any
    necessary subtitutions by referencing the SoSMap() associated with the
    parser.

    Ideally a new parser subclass will only need to set the class level attrs
    in order to be fully functional.

    :param conf_file: The configuration file to read from
    :type conf_file: ``str``

    :cvar name:     The parser name, used in logging errors
    :vartype name: ``str``

    :cvar regex_patterns:   A list of regex patterns to iterate over for every
                            line processed
    :vartype regex_patterns: ``list``

    :cvar mapping: Used by the parser to store and obfuscate matches
    :vartype mapping: ``SoSMap()``


    :cvar map_file_key: The key in the ``map_file`` to read when loading
                        previous obfuscation matches
    :vartype map_file_key: ``str``
    """

    name = 'Undefined Parser'
    regex_patterns = []
    skip_line_patterns = []
    skip_files = []
    map_file_key = 'unset'

    def __init__(self, config={}):
        self.regexes = {}
        if self.map_file_key in config:
            self.mapping.conf_update(config[self.map_file_key])

    def generate_item_regexes(self):
        """Generate regexes for items the parser will be searching for
        repeatedly without needing to generate them for every file and/or line
        we process

        Not used by all parsers.
        """
        pass

    def parse_line(self, line):
        """This will be called for every line in every file we process, so that
        every parser has a chance to scrub everything.

        :param line: The line to parse for possible matches for obfuscation
        :type line: ``str``

        :returns: The obfsucated line, and the number of changes made
        :rtype: ``tuple``, ``(str, int))``
        """
        count = 0
        for skip_pattern in self.skip_line_patterns:
            if re.match(skip_pattern, line, re.I):
                return line, count
        for pattern in self.regex_patterns:
            matches = [m[0] for m in re.findall(pattern, line, re.I)]
            if matches:
                matches.sort(reverse=True, key=lambda x: len(x))
                count += len(matches)
                for match in matches:
                    match = match.strip()
                    new_match = self.mapping.get(match)
                    if new_match != match:
                        line = line.replace(match, new_match)
        return line, count

    def parse_string_for_keys(self, string_data):
        """Parse a given string for instances of any obfuscated items, without
        applying the normal regex comparisons first. This is mainly used to
        obfuscate filenames that have, for example, hostnames in them.

        Rather than try to regex match the string_data, just use the builtin
        checks for substrings matching known obfuscated keys

        :param string_data: The line to be parsed
        :type string_data: ``str``

        :returns: The obfuscated line
        :rtype: ``str``
        """
        for pair in sorted(self.mapping.dataset.items(), reverse=True,
                           key=lambda x: len(x[0])):
            key, val = pair
            if key in self.mapping.skip_keys:
                continue
            if key in string_data:
                string_data = string_data.replace(key, val)
        return string_data

    def get_map_contents(self):
        """Get the contents of the mapping used by the parser

        :returns: All matches and their obfuscate counterparts
        :rtype: ``dict``
        """
        return self.mapping.dataset
