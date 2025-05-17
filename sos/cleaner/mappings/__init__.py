# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re, os, tempfile
import sqlite3, time
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

    def __init__(self, concur_backend, workdir):
        # TODO: ALL mappings must be deterministic; NO randomization in hostname or ip(6) mapper!
        self.dataset = {}  # TODO: mention the child classes can update it as well as add_sanitised_item_to_dataset method, so sqlite or files dont neet to have all counter values stored; e.g. when adding an IP address - sqlite and files approach guarantees same input is added in all processes at the same ordering - it can add a new network to the dataset. So dataset bumps by 2
        self._regexes_made = set()
        self.compiled_regexes = []
        self.cname = self.__class__.__name__.lower()
        # TODO: ensure the directory <workdir> does exist - but only when concur_backend='files'
        # TODO: deal with permissions..? IMHO default ones are OK
        self.workdir = workdir
        self.link_dir = os.path.join(self.workdir, 'cleaner_links', self.cname) #TODO: some better dir name?
        self.concur_backend = concur_backend
        self.load_entries()

    def unload_entries(self):
        self.sqlconn = self.sqlcursor = None

    def load_entries(self): # originally this was in __init__, but we need to trigger after cloning processes, and also reload content in files or sqlite DB in parent archive class, once children are done
        # TODO: call load_entries at beginning of obfuscation (list of) *files*
        if self.concur_backend == 'files':
            Path(self.link_dir).mkdir(parents=True, exist_ok=True)
            self.load_new_entries_from_dir(1) # if there are already stored items, load them first
        elif self.concur_backend == 'sql':
            Path(os.path.join(self.workdir, 'sqlite_cache')).mkdir(parents=True, exist_ok=True)
            self.sqlconn = sqlite3.connect(os.path.join(self.workdir, 'sqlite_cache' , f"{self.cname}.db"), check_same_thread=False) # TODO: better name?
            self.sqlconn.execute('pragma journal_mode = wal') # to improve DB locking on frequent concurrent writes
            self.sqlconn.execute('pragma temp_store = memory')  # 3 lines added from jcastillo's comment
            self.sqlconn.execute('pragma synchronous = normal')
            self.sqlconn.execute('pragma busy_timeout = 5000')
            self.sqlconn.execute('pragma mmap_size = 30000000000') # TODO: cant this be a problem on low performant systems? some kernel limitation behind..?
            self.sqlcursor = self.sqlconn.cursor()
            self.sqlcursor.execute(f"CREATE TABLE IF NOT EXISTS {self.cname} (counter, item)")
            self.sqlcursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ind_{self.cname}_counter_uniq ON {self.cname} (counter)")
            self.sqlcursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ind_{self.cname}_item_uniq ON {self.cname} (item)")
            self.sqlconn.commit()
            self.load_new_entries_from_db(1) # if there are already stored items, load them first

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

    def add_sanitised_item_to_dataset(self, item):
        try:
            self.dataset[item] = self.sanitize_item(item)
        except Exception as err:
            # TODO: add seomthing like self.log_debug(f"Unable to obfuscate {item}: {err}", caller=arc_name)
            self.dataset[item] = item
        if self.compile_regexes:
            self.add_regex_item(item)

    def load_new_entries_from_dir(self, counter):
        # TODO: this is a performance hack; there can be gaps in counter values as e.g. #14 is an IP address (in file)
        # while #15 is its network (in dataset but not in files). So the next file number is 16. The diffs should be
        # at most 2, but let be conservative and test next 5 numbers "only".
        no_files_cnt = 5
        while no_files_cnt > 0:
            fname = os.path.join(self.link_dir, f"{counter}")
            while os.path.isfile(fname):
                no_files_cnt = 5
                with open(fname, 'r') as f:
                    item = f.read()
                if not self.dataset.get(item, False):
                    self.add_sanitised_item_to_dataset(item)
                counter += 1
                fname = os.path.join(self.link_dir, f"{counter}")
            # no next file, but try a new next ones until no_files_cnt==0
            no_files_cnt -= 1
            counter += 1

    def load_new_entries_from_db(self, counter):
        if not self.sqlconn:
            self.load_entries()
        resp = self.sqlcursor.execute(f"SELECT * FROM {self.cname} WHERE counter>={counter} ORDER BY counter ASC")
        for _, item in resp.fetchall():
            if not self.dataset.get(item, False):
                self.add_sanitised_item_to_dataset(item)

    def add(self, item):
        """Add a particular item to the map, generating an obfuscated pair
        for it.

        Positional arguments:

            :param item:        The plaintext object to obfuscate
        """
        if self.ignore_item(item):
            return item

        if self.concur_backend == 'files':
            tmpfile = None
            while not self.dataset.get(item, False):
                if not tmpfile:
                    tmpfile = tempfile.NamedTemporaryFile(dir=self.link_dir)
                    with open(tmpfile.name, 'w') as f:
                        f.write(item)
                try:
                    counter = len(self.dataset) + 1
                    os.link(tmpfile.name, os.path.join(self.link_dir, f"{counter}"))
                    self.add_sanitised_item_to_dataset(item)
                except FileExistsError:
                    self.load_new_entries_from_dir(counter)

        elif self.concur_backend == 'sql':
            self.load_new_entries_from_db(1)
            while not self.dataset.get(item, False):
                try:
                    counter = len(self.dataset) + 1
                    self.sqlcursor.execute(f"INSERT INTO {self.cname} VALUES ({counter}, '{item}')")
                    self.sqlconn.commit()
                    self.add_sanitised_item_to_dataset(item)
                except sqlite3.IntegrityError as e:
                    print(f"    {os.getpid()}-{self.cname}: sql conflict for counter={counter} when inserting {item}")  # TODO: remove this
                    self.load_new_entries_from_db(counter)
                except sqlite3.OperationalError as e:
                    print(f"    {os.getpid()}-{self.cname}: sql ERROR for counter={counter} when inserting {item}") # TODO: remove this (here we can get a live-lock..)
                    self.unload_entries()
                    time.sleep(1)
                    self.load_entries()
                    self.load_new_entries_from_db(counter)
                except Exception as e:
                    print(f"    {os.getpid()}-{self.cname}: sql generic ERROR {e} for counter={counter} when inserting {item}") # TODO: remove this
                    raise e
        else:
            self.add_sanitised_item_to_dataset(item)

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
