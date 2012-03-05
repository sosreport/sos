#!/usr/bin/env python

import unittest
import os
import tarfile
import zipfile

from sos.utilities import TarFileArchive, ZipFileArchive

class ZipFileArchiveTest(unittest.TestCase):

    def setUp(self):
        self.zf = ZipFileArchive('test')

    def tearDown(self):
        os.unlink('test.zip')

    def check_for_file(self, filename):
        zf = zipfile.ZipFile('test.zip', 'r')
        zf.getinfo(filename)
        zf.close()

    def test_create(self):
        self.zf.close()

    def test_add_file(self):
        self.zf.add_file('tests/ziptest')
        self.zf.close()

        self.check_for_file('test/tests/ziptest')

    def test_add_dir(self):
        self.zf.add_file('tests/')
        self.zf.close()

        self.check_for_file('test/tests/ziptest')

    def test_add_renamed(self):
        self.zf.add_file('tests/ziptest', dest='tests/ziptest_renamed')
        self.zf.close()

        self.check_for_file('test/tests/ziptest_renamed')

    def test_add_renamed_dir(self):
        self.zf.add_file('tests/', 'tests_renamed/')
        self.zf.close()

        self.check_for_file('test/tests_renamed/ziptest')

    def test_add_string(self):
        self.zf.add_string('this is content', 'tests/string_test.txt')
        self.zf.close()

        self.check_for_file('test/tests/string_test.txt')

    def test_get_file(self):
        self.zf.add_string('this is my content', 'tests/string_test.txt')

        afp = self.zf.open_file('tests/string_test.txt')
        self.assertEquals('this is my content', afp.read())

    def test_overwrite_file(self):
        self.zf.add_string('this is my content', 'tests/string_test.txt')
        self.zf.add_string('this is my new content', 'tests/string_test.txt')

        afp = self.zf.open_file('tests/string_test.txt')
        self.assertEquals('this is my new content', afp.read())

    def test_make_link(self):
        self.zf.add_file('tests/ziptest')
        self.zf.add_link('tests/ziptest', 'link_name')

        self.zf.close()
        try:
            self.check_for_file('test/link_name')
            self.fail("link should not exist")
        except KeyError:
            pass

    def test_compress(self):
        self.assertEquals(self.zf.compress("zip"), self.zf.name())

class TarFileArchiveTest(unittest.TestCase):

    def setUp(self):
        self.tf = TarFileArchive('test')

    def tearDown(self):
        os.unlink(self.tf.name())

    def check_for_file(self, filename):
        rtf = tarfile.open('test.tar')
        rtf.getmember(filename)
        rtf.close()

    def test_create(self):
        self.tf.close()
        self.assertTrue(os.path.exists('test.tar'))

    def test_add_file(self):
        self.tf.add_file('tests/ziptest')
        self.tf.close()

        self.check_for_file('test/tests/ziptest')

    def test_add_dir(self):
        self.tf.add_file('tests/')
        self.tf.close()

        self.check_for_file('test/tests/ziptest')

    def test_add_renamed(self):
        self.tf.add_file('tests/ziptest', dest='tests/ziptest_renamed')
        self.tf.close()

        self.check_for_file('test/tests/ziptest_renamed')

    def test_add_renamed_dir(self):
        self.tf.add_file('tests/', 'tests_renamed/')
        self.tf.close()

        self.check_for_file('test/tests_renamed/ziptest')

    def test_add_string(self):
        self.tf.add_string('this is content', 'tests/string_test.txt')
        self.tf.close()

        self.check_for_file('test/tests/string_test.txt')

    def test_get_file(self):
        self.tf.add_string('this is my content', 'tests/string_test.txt')

        afp = self.tf.open_file('tests/string_test.txt')
        self.assertEquals('this is my content', afp.read())

    def test_overwrite_file(self):
        self.tf.add_string('this is my content', 'tests/string_test.txt')
        self.tf.add_string('this is my new content', 'tests/string_test.txt')

        afp = self.tf.open_file('tests/string_test.txt')
        self.assertEquals('this is my new content', afp.read())

    def test_make_link(self):
        self.tf.add_file('tests/ziptest')
        self.tf.add_link('tests/ziptest', 'link_name')

        self.tf.close()
        self.check_for_file('test/link_name')

    def test_compress(self):
        name = self.tf.compress("gzip")

if __name__ == "__main__":
    unittest.main()
