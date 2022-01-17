# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.mappings import SoSMap


class SoSUsernameMap(SoSMap):
    """Mapping to store usernames matched from ``lastlog`` output.

    Usernames are obfuscated as ``obfuscateduserX`` where ``X`` is a counter
    that gets incremented for every new username found.

    Note that this specifically obfuscates user_names_ and not UIDs.
    """

    name_count = 0

    def load_names_from_options(self, opt_names):
        for name in opt_names:
            if name and name not in self.dataset.keys():
                self.add(name)

    def sanitize_item(self, username):
        """Obfuscate a new username not currently found in the map
        """
        ob_name = "obfuscateduser%s" % self.name_count
        self.name_count += 1
        if ob_name in self.dataset.values():
            return self.sanitize_item(username.lower())
        return ob_name
