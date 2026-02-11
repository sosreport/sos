# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
import os
import tempfile
from pathlib import Path


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
    ignore_short_items = False
    match_full_words_only = False

    def __init__(self, workdir):
        self.dataset = {}
        self._regexes_made = set()
        self.compiled_regexes = []
        self.cname = self.__class__.__name__.lower()
        # workdir's default value '/tmp' is used just by avocado tests,
        # otherwise we override it to /etc/sos/cleaner (or map_file dir)
        self.workdir = workdir
        self.cache_dir = os.path.join(self.workdir, 'cleaner_cache',
                                      self.cname)
        self.load_entries()

    def load_entries(self):
        """ Load cached entries from the disk. This method must be called when
        we initialize a Map instance and whenever we want to retrieve
        self.dataset (e.g. to store default_mapping file). The later is
        essential since a concurrent Map can add more objects to the cache,
        so we need to update self.dataset up to date.

        Keep in mind that size of self.dataset is usually bigger than number
        of files in the corresponding cleaner's directory: directory contains
        just whole items (e.g. IP addresses) while dataset contains more
        derived objects (e.g. subnets).
        """

        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        self.load_new_entries_from_dir(1)

    def ignore_item(self, item):
        """Some items need to be completely ignored, for example link-local or
        loopback addresses should not be obfuscated
        """
        if not item or item in self.skip_keys or item in self.dataset.values()\
                or (self.ignore_short_items and len(item) <= 3):
            return True
        for skip in self.ignore_matches:
            if re.match(skip, item, re.I):
                return True
        return False

    def insert_to_dataset(self, item, value):
        self.dataset[item] = value

    def add_sanitised_item_to_dataset(self, item):
        try:
            self.insert_to_dataset(item, self.sanitize_item(item))
        except Exception:
            # we failed to obfuscate the item as it is not a real IP address
            # or hostname or similar. Let return the original string and keep
            # the item->item "mapping" in dataset to save time the next time.
            self.insert_to_dataset(item, item)
        if self.compile_regexes:
            self.add_regex_item(item)

    def load_new_entries_from_dir(self, counter):
        # this is a performance hack; there can be gaps in counter values as
        # e.g. sanitised item #14 is an IP address (in file) while item #15
        # is its network (in dataset but not in files). So the next file
        # number is 16. The diffs should be at most 2, the above is so far
        # the only type of "underneath dataset growth". But let be
        # conservative and test next 5 numbers "only".
        no_files_cnt = 5
        while no_files_cnt > 0:
            fname = os.path.join(self.cache_dir, f"{counter}")
            while os.path.isfile(fname):
                no_files_cnt = 5
                with open(fname, 'r', encoding='utf-8') as f:
                    item = f.read()
                if not self.dataset.get(item, False):
                    self.add_sanitised_item_to_dataset(item)
                counter += 1
                fname = os.path.join(self.cache_dir, f"{counter}")
            # no next file, but try a new next ones until no_files_cnt==0
            no_files_cnt -= 1
            counter += 1

    def add(self, item):
        """Add a particular item to the map, generating an obfuscated pair
        for it.

        Positional arguments:

            :param item:        The plaintext object to obfuscate
        """
        if self.ignore_item(item):
            return item

        tmpfile = None
        while not self.dataset.get(item, False):
            if not tmpfile:
                # pylint: disable=consider-using-with
                tmpfile = tempfile.NamedTemporaryFile(dir=self.cache_dir)
                with open(tmpfile.name, 'w', encoding='utf-8') as f:
                    f.write(item)
            try:
                counter = len(self.dataset) + 1
                os.link(tmpfile.name, os.path.join(self.cache_dir,
                                                   f"{counter}"))
                self.add_sanitised_item_to_dataset(item)
            except FileExistsError:
                self.load_new_entries_from_dir(counter)

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
        if self.match_full_words_only:
            item = rf'(?<![a-z0-9]){re.escape(item)}(?=\b|_|-)'
        else:
            item = re.escape(item)
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

    def conf_update(self, config):
        """Update the map using information from a previous run to ensure that
        we have consistent obfuscation between reports

        Positional arguments:

            :param config:    A dict of mappings with the form of
                              {clean_entry: 'obfuscated_entry'}
        """
        self.dataset.update(config)
