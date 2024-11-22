# Copyright 2023 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from sos.cleaner.preppers import SoSPrepper


class KeywordPrepper(SoSPrepper):
    """
    Prepper to handle keywords passed to cleaner via either the `--keywords`
    or `--keyword-file` options.
    """

    name = 'keyword'

    # pylint: disable=unused-argument
    def _get_items_for_keyword(self, archive):
        items = []
        for kw in self.opts.keywords:
            items.append(kw)
        if self.opts.keyword_file and os.path.exists(self.opts.keyword_file):
            with open(self.opts.keyword_file, 'r', encoding='utf-8') as kwf:
                items.extend(kwf.read().splitlines())

        for item in items:
            self.regex_items['keyword'].add(item)

        return items

# vim: set et ts=4 sw=4 :
