# Copyright 2026 Red Hat, Inc. Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.regexp_map import SoSRegexpMap


class SoSRegexpParser(SoSCleanerParser):
    """Parser for user-defined regular expressions from --regexp-file.

    Unlike other parsers, this does not define static patterns. Patterns
    are loaded by RegexpPrepper and transferred here via regexp_patterns
    dict.

    For each line, iterates all user patterns, extracts capturing groups,
    and calls SoSRegexpMap to generate obfuscated<keyword><number>
    values. See RegexpPrepper for pattern validation and SoSRegexpMap for
    obfuscation.
    """

    name = 'Regexp Parser'
    map_file_key = 'regexp_map'
    compile_regexes = False  # We handle our own regex matching

    def __init__(self, config, workdir, skip_cleaning_files=None):
        if skip_cleaning_files is None:
            skip_cleaning_files = []
        self.mapping = SoSRegexpMap(workdir)
        super().__init__(config, skip_cleaning_files)
        # Will be populated by prepper with {name: compiled_pattern}
        self.regexp_patterns = {}

    def _parse_line(self, line):
        """Parse line against all registered regexp patterns.

        For each pattern that matches, extract ALL capturing groups
        and obfuscate them using the pattern's keyword.
        """
        count = 0
        for keyword, pattern in self.regexp_patterns.items():
            # Collect all matches for this pattern
            matches = list(pattern.finditer(line))

            # Process matches right-to-left to avoid position shifts
            for match in reversed(matches):
                # Extract the captured group (group 1)
                captured_value = match.group(1)

                # Tell the mapping which keyword this value belongs to
                self.mapping.set_keyword_for_item(captured_value, keyword)

                # Get or create the obfuscated value
                obfuscated = self.mapping.get(captured_value)

                # Replace the captured group in the line
                # We need to replace the full match but only obfuscate group 1
                full_match = match.group(0)
                # Reconstruct by replacing group 1 in the full match
                replacement = full_match.replace(captured_value, obfuscated, 1)
                # Use span() to replace at exact position
                start, end = match.span()
                line = line[:start] + replacement + line[end:]
                count += 1

        return line, count
