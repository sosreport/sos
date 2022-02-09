# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re

from threading import Lock


class SoSMap():
    """Standardized way to store items with their obfuscated counterparts.

    Each type of sanitization that SoSCleaner supports should have a
    corresponding SoSMap() object, to allow for easy retrieval of obfuscated
    items.
    """
    # used for regex skips in parser.parse_line()
    ignore_matches = []
    # used for filename obfuscations in parser.parse_string_for_keys()
    skip_keys = []
    compile_regexes = True

    def __init__(self):
        self.dataset = {}
        self._regexes_made = set()
        self.compiled_regexes = []
        self.lock = Lock()

    def ignore_item(self, item):
        """Some items need to be completely ignored, for example link-local or
        loopback addresses should not be obfuscated
        """
        if not item or item in self.skip_keys or item in self.dataset.values():
            return True
        for skip in self.ignore_matches:
            if re.match(skip, item):
                return True

    def add(self, item):
        """Add a particular item to the map, generating an obfuscated pair
        for it.

        Positional arguments:

            :param item:        The plaintext object to obfuscate
        """
        if self.ignore_item(item):
            return item
        with self.lock:
            self.dataset[item] = self.sanitize_item(item)
            if self.compile_regexes:
                self.add_regex_item(item)
            return self.dataset[item]

    def add_regex_item(self, item):
        """Add an item to the regexes dict and then re-sort the list that the
        parsers will use during parse_line()

        :param item:    The unobfuscated item to generate a regex for
        :type item:     ``str``
        """
        if self.ignore_item(item):
            return
        if item not in self._regexes_made:
            # save the item in a set to avoid clobbering existing regexes,
            # as searching this set is significantly faster than searching
            # through the actual compiled_regexes list, especially for very
            # large collections of entries
            self._regexes_made.add(item)
            # add the item, Pattern tuple directly to the compiled_regexes list
            # and then sort the existing list, rather than rebuild the list
            # from scratch every time we add something like we would do if we
            # tracked/saved the item and the Pattern() object in a dict or in
            # the set above
            self.compiled_regexes.append((item, self.get_regex_result(item)))
            self.compiled_regexes.sort(key=lambda x: len(x[0]), reverse=True)

    def get_regex_result(self, item):
        """Generate the object/value that is used by the parser when iterating
        over pre-generated regexes during parse_line(). For most parsers this
        will simply be a ``re.Pattern()`` object, but for more complex parsers
        this can be overridden to provide a different object, e.g. a tuple,
        for that parer's specific iteration needs.

        :param item:    The unobfuscated string to generate the regex for
        :type item:     ``str``

        :returns:       A compiled regex pattern for the item
        :rtype:         ``re.Pattern``
        """
        return re.compile(item, re.I)

    def sanitize_item(self, item):
        """Perform the obfuscation relevant to the item being added to the map.

        This should be overridden by each type of map that subclasses SoSMap

        Positional arguments:

            :param item:        The plaintext object to obfuscate
        """
        return item

    def get(self, item):
        """Retrieve an item's obfuscated counterpart from the map. If the item
        does not yet exist in the map, add it by generating one on the fly
        """
        if self.ignore_item(item):
            return item
        if item not in self.dataset:
            return self.add(item)
        return self.dataset[item]

    def conf_update(self, map_dict):
        """Update the map using information from a previous run to ensure that
        we have consistent obfuscation between reports

        Positional arguments:

            :param map_dict:    A dict of mappings with the form of
                                {clean_entry: 'obfuscated_entry'}
        """
        self.dataset.update(map_dict)
