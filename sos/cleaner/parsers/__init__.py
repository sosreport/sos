# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import re


class SoSCleanerParser():
    """Parsers are used to build objects that will take a line as input,
    parse it for a particular pattern (E.G. IP addresses) and then make any
    necessary subtitutions by referencing the SoSMap() associated with the
    parser.

    Ideally a new parser subclass will only need to set the class level attrs
    in order to be fully functional.

        :attr name str:                 The parser name, used in logging errors

        :attr regex_patterns list:      A list of regex patterns to iterate
                                        over for every line processed
        :attr mapping SoSMap:           A SoSMap used by the parser to store
                                        and obfuscate pattern matches
        :attr map_file_key str:         The key in the map_file to read when
                                        loading previous obfuscation matches
        :attr prep_map_file str:        Filename to attempt to read from an
                                        archive to pre-seed the map with
                                        matches. E.G. ip_addr for loading IP
                                        addresses into the SoSIPMap.
    """

    name = 'Undefined Parser'
    regex_patterns = []
    map_file_key = 'unset'
    prep_map_file = 'unset'

    def __init__(self, conf_file=None):
        # attempt to load previous run data into the mapping for the parser
        if conf_file:
            try:
                with open(conf_file, 'r') as map_file:
                    _default_mappings = json.load(map_file)
                if self.map_file_key in _default_mappings:
                    self.mapping.conf_update(
                        _default_mappings[self.map_file_key]
                    )
            except IOError:
                pass

    def parse_line(self, line):
        """This will be called for every line in every file we process, so that
        every parser has a chance to scrub everything.
        """
        count = 0
        for pattern in self.regex_patterns:
            matches = [m[0] for m in re.findall(pattern, line, re.I)]
            if matches:
                count += len(matches)
                for match in matches:
                    new_match = self.mapping.get(match.strip())
                    line = line.replace(match.strip(), new_match)
        return line, count

    def get_map_contents(self):
        """Return the contents of the mapping used by the parser
        """
        return self.mapping.dataset
