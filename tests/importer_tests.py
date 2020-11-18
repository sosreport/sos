# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import unittest

from sos.utilities import ImporterHelper


class ImporterHelperTests(unittest.TestCase):

    def test_runs(self):
        h = ImporterHelper(unittest)
        modules = h.get_modules()
        self.assertTrue('main' in modules)


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
