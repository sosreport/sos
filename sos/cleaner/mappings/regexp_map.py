# Copyright 2026 Red Hat, Inc. Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import logging
import re
from sos.cleaner.mappings import SoSMap


class SoSRegexpMap(SoSMap):
    """Runtime obfuscation mapping for user-defined regex patterns.

    The class maintains per-keyword counters, generates obfuscated
    values, persists state. See RegexpPrepper for pattern
    loading/validation.

    Does not define patterns - relies on RegexpPrepper loading from
    --regexp-file. Parser finds matches, this map generates
    obfuscation.

    Obfuscation: Each keyword has independent counter starting at 0.
    Example:
        Pattern: shorthost host=([^,\\s]+)(?:,|$)
        Input:   "host=foobar,os=rhel9"
        Output:  "host=obfuscatedshorthost0,os=rhel9"
        Next:    "host=obfuscatedshorthost1,..."

    Persistence:
    - Map file: {"foobar": "obfuscatedshorthost5"} → counter
      restored to 6
    - Cache files (multi-process): ["keyword", "item"] JSON arrays,
      DIFFERENT from other Map classes.

    Keywords cannot end with digits to avoid ambiguity parsing
    obfuscated values: for keyword "api2", "obfuscatedapi25" can be
    interpreted as either:
      - keyword="api2", counter=5, or
      - keyword="api", counter=25
    """

    # Regexp patterns define their own matching boundaries, so we don't
    # need word boundaries or token lookup.
    match_full_words_only = False
    use_token_lookup = False
    compile_regexes = False  # Prepper does its own compile

    # Pattern to parse obfuscated values: obfuscated + keyword + counter
    # Greedy [a-z0-9]* stops at last letter before trailing digits
    # Examples: obfuscatedshorthost10 → keyword="shorthost", counter=10
    #           obfuscatedapi2key5 → keyword="api2key", counter=5
    _OBFUSCATED_PATTERN = re.compile(
        r'^obfuscated([a-z0-9]*[a-z])(\d+)$'
    )

    def __init__(self, workdir, _static_regex=None):
        # Initialize these BEFORE calling super().__init__() because the
        # parent will call load_entries() -> load_new_entries_from_dir()
        # which needs them
        # Map of keyword -> counter for each keyword type
        self.keyword_counts = {}
        # Map of item -> keyword (so we know which keyword matched)
        self.item_keywords = {}
        # Logger for warning/error messages
        self.soslog = logging.getLogger('sos')

        super().__init__(workdir, _static_regex)

        # Initialize keywords' counters from any pre-loaded dataset
        self._initialize_counters_from_dataset()

    def _initialize_counters_from_dataset(self):
        """Initialize keyword counters from pre-loaded dataset.

        If dataset was loaded from a previous run (via --map-file or cache
        dir), we need to initialize counters to avoid generating duplicate
        obfuscated values.

        Parses existing obfuscated values like "obfuscatedshorthost5" to
        extract the keyword and counter, then sets each keyword's counter
        to max(existing) + 1.

        This method RESETS keyword_counts from scratch based on dataset,
        so it can be called multiple times (e.g., after conf_update).
        """
        # Reset counters - we'll rebuild from dataset
        self.keyword_counts = {}

        for obfuscated_value in self.dataset.values():
            match = self._OBFUSCATED_PATTERN.match(obfuscated_value)
            if match:
                keyword = match.group(1)
                counter = int(match.group(2))
                # Set counter to max(current, this_counter + 1) for next
                # available value
                next_value = self.keyword_counts.get(keyword, 0)
                self.keyword_counts[keyword] = max(next_value, counter + 1)
            else:
                # Malformed obfuscated value - log warning
                self.soslog.warning(
                    f"Cannot extract keyword from obfuscated value "
                    f"'{obfuscated_value}' - skipping its counter "
                    f"initialization"
                )

    def conf_update(self, config):
        """Override to extract keyword-to-item associations from map file.

        When loading from a previous run's map file, we need to restore
        the item→keyword associations so that load_new_entries_from_dir()
        can properly re-sanitize items from cache.

        Parses obfuscated values like "obfuscatedshorthost5" to extract
        the keyword, then associates it with the original item.
        """
        for item, obfuscated_value in config.items():
            match = self._OBFUSCATED_PATTERN.match(obfuscated_value)
            if match:
                keyword = match.group(1)
                self.item_keywords[item] = keyword
            else:
                # Malformed obfuscated value - log warning
                self.soslog.warning(
                    f"Cannot extract keyword from obfuscated value "
                    f"'{obfuscated_value}' for item '{item}'"
                )

        # Call parent to update dataset
        super().conf_update(config)

        # Re-initialize counters from the updated dataset to ensure
        # keyword_counts reflects all items from the map file
        self._initialize_counters_from_dataset()

    def _read_item_from_cache_file(self, fname):
        """Read item and keyword from JSON cache file.

        Cache files for regexp map are JSON arrays with format:
        ["keyword", "item"]

        Example: ["myshorthost", "foobar"]

        This preserves the keyword association needed for proper obfuscation.

        :param fname:  Full path to the cache file
        :returns:      The item to add to the dataset, or None to skip
        """
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) == 2:
                    keyword, item = data
                    # Restore the keyword association
                    self.item_keywords[item] = keyword
                    return item

                self.soslog.warning(
                    f"Cache file {fname} has invalid format, "
                    f"expected [keyword, item] array, skipping"
                )
                return None
        except json.JSONDecodeError:
            self.soslog.warning(
                f"Cache file {fname} contains invalid JSON, skipping"
            )
            return None

    def _write_item_to_cache_file(self, item, tmpfile):
        """Write item and keyword as JSON array to cache file.

        Format: [keyword, item]
        Example: ["myshorthost", "foobar"]

        :param item:     The item to write
        :param tmpfile:  The temporary file to write to
        """
        # Get the keyword for this item - must exist, set by parser, but
        # let support the 'unknown' fallback also here (see sanitize_item)
        keyword = self.item_keywords.get(item, 'unknown')

        # Write JSON array: [keyword, item]
        with open(tmpfile.name, 'w', encoding='utf-8') as f:
            json.dump([keyword, item], f)

    def set_keyword_for_item(self, item, keyword):
        """Associate an item with its keyword for obfuscation.

        This should be called when adding items to the map, so that
        sanitize_item knows which keyword pattern matched.
        """
        self.item_keywords[item] = keyword

    def sanitize_item(self, item):
        if item in self.dataset:
            return self.dataset[item]

        # Get the keyword for this item
        # This should always be present - if not, it's a bug in the parser
        keyword = self.item_keywords.get(item, None)
        if keyword is None:
            # This should never happen - log error and use fallback
            self.soslog.error(
                f"Regexp item '{item}' has no associated keyword. "
                f"This indicates a bug in the regexp parser. "
                f"Using fallback name 'unknown'."
            )
            keyword = 'unknown'

        # Get and increment counter for this keyword
        count = self.keyword_counts.get(keyword, 0)
        _ob_item = f"obfuscated{keyword}{count}"
        self.keyword_counts[keyword] = count + 1

        return _ob_item
