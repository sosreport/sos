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

    def __init__(self):
        self.dataset = {}
        self.lock = Lock()

    def ignore_item(self, item):
        """Some items need to be completely ignored, for example link-local or
        loopback addresses should not be obfuscated
        """
        for skip in self.ignore_matches:
            if re.match(skip, item):
                return True

    def item_in_dataset_values(self, item):
        return item in self.dataset.values()

    def add(self, item):
        """Add a particular item to the map, generating an obfuscated pair
        for it.

        Positional arguments:

            :param item:        The plaintext object to obfuscate
        """
        with self.lock:
            if not item:
                return item
            self.dataset[item] = self.sanitize_item(item)
            return self.dataset[item]

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
        if (not item or self.ignore_item(item) or
                self.item_in_dataset_values(item)):
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
