# Copyright 2026 Red Hat, Inc. Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import re

from sos.cleaner.preppers import SoSPrepper


class RegexpPrepper(SoSPrepper):
    r"""
    Load and validate user-defined regex patterns from --regexp-file.

    The class reads config file, validates syntax, transfers patterns
    to parser. See SoSRegexpMap for runtime obfuscation behavior.

    File format (lines starting with '#' are comments):
        <keyword> <pattern>

    - keyword: lowercase alphanumeric, ending with letter only
    - pattern: Python regex with EXACTLY ONE capturing group () marking
               sensitive data to obfuscate as
               'obfuscated<keyword><number>'

    Use non-capturing groups (?:...) for additional matching logic, to
    keep the "exactly one capturing group".

    Examples:
        shorthost host=([^,\\s]+)(?:,|$)
            → "host=foobar," becomes "host=obfuscatedshorthost0,"

        webhost (?:https?:\/\/|www\.)([a-zA-Z0-9.-]*[a-zA-Z0-9])
            → "https://foohost" becomes "https://obfuscatedwebhost0"

        apikey api(?:_key|key)=([a-zA-Z0-9]+)
            → Matches both "api_key=" and "apikey=", obfuscates value
              only

    Rejected patterns: keyword ends with digit, uppercase letters,
    reserved names (host, ip, mac, user, etc.), no capturing group,
    multiple groups.
    """

    name = 'regexp'

    # Reserved names from other mapping types that cannot be used
    # to avoid confusion with their obfuscation patterns
    RESERVED_NAMES = {
        'host',      # hostname_map: produces 'host1', 'host2', etc.
        'hostname',  # alias for host
        'domain',    # hostname_map: domain handling
        'ip',        # ip_map: produces IP addresses like 10.x.x.x
        'ipv6',      # ipv6_map: produces IPv6 addresses
        'mac',       # mac_map: produces MAC addresses like 53:4f:53:x:x:x
        'word',      # keyword_map: produces 'obfuscatedword1', etc.
        'keyword',   # alias for word
        'user',      # username_map: produces 'obfuscateduser1', etc.
        'username',  # alias for user
    }

    def __init__(self, options):
        super().__init__(options)
        # Map of name -> compiled regex pattern
        self.regexp_map = {}
        # Reference to the parser (will be set later)
        self.parser = None

    # pylint: disable=unused-argument
    def _get_items_for_regexp(self, archive):
        """Load regexp patterns from file and store in regexp_map.

        This method does not return items because regexp patterns work
        differently - they need to be matched by the parser with knowledge
        of which keyword pattern matched. The regexp_map is transferred
        to the parser via set_parser().

        :returns: Empty list (patterns are not items to obfuscate)
        """

        if not self.opts.regexp_file:
            return []

        if not os.path.exists(self.opts.regexp_file):
            self.log_debug(
                f"Regexp patterns file not found: "
                f"{self.opts.regexp_file}"
            )
            return []

        self.log_info(
            f"Loading regexp patterns from {self.opts.regexp_file}"
        )

        with open(self.opts.regexp_file, 'r', encoding='utf-8') as regexpf:
            for line_num, line in enumerate(regexpf, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Parse name and pattern (split on first whitespace)
                parts = line.split(None, 1)
                if len(parts) != 2:
                    self.log_error(
                        f"Line {line_num}: Invalid format, "
                        f"expected 'name pattern'. Skipping line: {line}"
                    )
                    continue

                name, pattern = parts

                # Validate keyword format
                # Must be lowercase alphanumeric, start with letter, not
                # end with digit
                if not re.match(r'^[a-z0-9]*[a-z]$', name):
                    self.log_error(
                        f"Line {line_num}: Keyword '{name}' must contain "
                        f"only lowercase letters and digits and end with a "
                        f"lowercase letter. Skipping."
                    )
                    continue

                # Check if name is a reserved word
                if name in self.RESERVED_NAMES:
                    self.log_error(
                        f"Line {line_num}: Pattern name '{name}' is "
                        f"reserved for built-in obfuscation types. "
                        f"Reserved names: "
                        f"{', '.join(sorted(self.RESERVED_NAMES))}. "
                        f"Please choose a different name. Skipping."
                    )
                    continue

                # Validate the regular expression
                try:
                    compiled_pattern = re.compile(pattern)

                    # Check if pattern contains exactly one capturing group
                    num_groups = compiled_pattern.groups
                    if num_groups != 1:
                        self.log_error(
                            f"Line {line_num}: Pattern '{name}' must "
                            f"contain exactly one capturing group (). "
                            f"Found {num_groups} groups. Use "
                            f"non-capturing groups (?:...) for additional "
                            f"matching logic. Skipping."
                        )
                        continue

                    # Store in map, log if overriding existing keyword
                    # name.
                    if name in self.regexp_map:
                        self.log_info(
                            f"Line {line_num}: Duplicate name '{name}'. "
                            f"Previous pattern will be overwritten."
                        )
                    self.regexp_map[name] = compiled_pattern
                    self.log_debug(f"Loaded pattern '{name}': {pattern}")

                except re.error as e:
                    self.log_error(
                        f"Line {line_num}: Invalid regex pattern "
                        f"for '{name}': {e}. Skipping."
                    )
                    continue

        self.log_info(f"Loaded {len(self.regexp_map)} regexp patterns")
        return []

    def set_parser(self, parser):
        """Transfer loaded patterns to the regexp parser.

        This should be called after patterns are loaded to give the
        parser access to the compiled patterns and their keywords.
        """
        parser.regexp_patterns = self.regexp_map
        self.log_debug(
            f"Transferred {len(self.regexp_map)} patterns to parser"
        )

# vim: set et ts=4 sw=4 :
