#!/usr/bin/env python

import unittest
import os
import tarfile
import zipfile
import tempfile
import shutil

from sos.archive import TarFileArchive
from sos.utilities import tail
from sos.policies import Policy

# PYCOMPAT
import six


class TarFileArchiveTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tf = TarFileArchive('test', self.tmpdir, Policy(), 1)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def check_for_file(self, filename):
        rtf = tarfile.open(os.path.join(self.tmpdir, 'test.tar'))
        rtf.getmember(filename)
        rtf.close()

    def test_create(self):
        self.tf.finalize('auto')
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir,
                                                    'test.tar')))

    def test_add_file(self):
        self.tf.add_file('tests/ziptest')
        self.tf.finalize('auto')

        self.check_for_file('test/tests/ziptest')

    def test_add_node_dev_null(self):
        st = os.lstat('/dev/null')
        dev_maj = os.major(st.st_rdev)
        dev_min = os.minor(st.st_rdev)
        self.tf.add_node('/dev/null', st.st_mode, os.makedev(dev_maj, dev_min))

    # when the string comes from tail() output
    def test_add_string_from_file(self):
        self.copy_strings = []
        testfile = tempfile.NamedTemporaryFile(dir=self.tmpdir, delete=False)
        testfile.write(six.b("*" * 1000))
        testfile.flush()
        testfile.close()

        self.copy_strings.append((tail(testfile.name, 100), 'string_test.txt'))
        self.tf.add_string(self.copy_strings[0][0], 'tests/string_test.txt')
        self.tf.finalize('auto')


# Since commit 179d9bb add_file does not support recursive directory
# addition. Disable this test for now.
#    def test_add_dir(self):
#        self.tf.add_file('tests/')
#        self.tf.close()
#
#        self.check_for_file('test/tests/ziptest')

    def test_add_renamed(self):
        self.tf.add_file('tests/ziptest', dest='tests/ziptest_renamed')
        self.tf.finalize('auto')

        self.check_for_file('test/tests/ziptest_renamed')

# Since commit 179d9bb add_file does not support recursive directory
# addition. Disable this test for now.
#    def test_add_renamed_dir(self):
#        self.tf.add_file('tests/', 'tests_renamed/')
#        self.tf.close()
#
#        self.check_for_file('test/tests_renamed/ziptest')

    def test_add_string(self):
        self.tf.add_string('this is content', 'tests/string_test.txt')
        self.tf.finalize('auto')

        self.check_for_file('test/tests/string_test.txt')

    def test_get_file(self):
        self.tf.add_string('this is my content', 'tests/string_test.txt')

        afp = self.tf.open_file('tests/string_test.txt')
        self.assertEquals('this is my content', afp.read())

    def test_rewrite_file(self):
        """Test that re-writing a file does not modify the content.

            In sos we do not have a use for overwriting archive content
            in-place (it is an error if different plugins attempt to
            store different content at the same path).

            We do not enforce the content check at runtime since it
            would be prohibitively costly: instead just verify in the
            unit suite that the original content is preserved.
        """
        self.tf.add_string('this is my content', 'tests/string_test.txt')
        self.tf.add_string('this is my new content', 'tests/string_test.txt')

        afp = self.tf.open_file('tests/string_test.txt')
        self.assertEquals('this is my content', afp.read())

    def test_make_link(self):
        self.tf.add_file('tests/ziptest')
        self.tf.add_link('tests/ziptest', 'link_name')

        self.tf.finalize('auto')
        self.check_for_file('test/link_name')

    def test_compress(self):
        self.tf.finalize("auto")

if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
