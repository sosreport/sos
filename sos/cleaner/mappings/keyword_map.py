# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.mappings import SoSMap


class SoSKeywordMap(SoSMap):
    """Mapping store for user provided keywords

    By default, this map will perform no matching or obfuscation. It relies
    entirely on the use of the --keywords option by the user.

    Any keywords provided are then obfuscated into 'obfuscatedwordX', where X
    is an incrementing integer.
    """

    word_count = 0

    def sanitize_item(self, item):
        _ob_item = "obfuscatedword%s" % self.word_count
        self.word_count += 1
        if _ob_item in self.dataset.values():
            return self.sanitize_item(item)
        return _ob_item
