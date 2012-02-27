import os.path
import unittest
from StringIO import StringIO

from sos.utilities import grep, DirTree, checksum
import sos

class GrepTest(unittest.TestCase):

    def test_file_obj(self):
        test_s = "\n".join(['this is only a test', 'there are only two lines'])
        test_fo = StringIO(test_s)
        matches = grep(".*test$", test_fo)
        self.assertEquals(matches, ['this is only a test\n'])

    def test_real_file(self):
        matches = grep(".*unittest$", __file__.replace(".pyc", ".py"))
        self.assertEquals(matches, ['import unittest\n'])

    def test_open_file(self):
        matches = grep(".*unittest$", open(__file__.replace(".pyc", ".py")))
        self.assertEquals(matches, ['import unittest\n'])


class DirTreeTest(unittest.TestCase):

    def test_makes_tree(self):
        # I'll admit, this a pretty lame test, but it will at least sniff out
        # some syntax issues
        t = DirTree(os.path.dirname(sos.__file__)).as_string()
        self.assertTrue('Makefile' in t)

class ChecksumTest(unittest.TestCase):

    def test_simple_hash(self):
        self.assertEquals(checksum(StringIO('this is a test'), algorithm="sha256"),
                '2e99758548972a8e8822ad47fa1017ff72f06f3ff6a016851f45c398732bc50c')
