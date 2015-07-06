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
