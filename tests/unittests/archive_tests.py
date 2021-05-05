# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import unittest
import os
import tarfile
import tempfile
import shutil

from sos.archive import TarFileArchive
from sos.utilities import tail
from sos.policies import Policy


class TarFileArchiveTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        enc = {'encrypt': False}
        self.tf = TarFileArchive('test', self.tmpdir, Policy(), 1, enc, '/')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def check_for_file(self, filename):
        rtf = tarfile.open(os.path.join(self.tmpdir, 'test.tar.xz'))
        rtf.getmember(filename)
        rtf.close()

    def test_create(self):
        self.tf.finalize('auto')
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir,
                                                    'test.tar.xz')))

    def test_add_file(self):
        self.tf.add_file('tests/unittests/ziptest')
        self.tf.finalize('auto')

        self.check_for_file('test/tests/unittests/ziptest')

    def test_add_node_dev_null(self):
        st = os.lstat('/dev/null')
        dev_maj = os.major(st.st_rdev)
        dev_min = os.minor(st.st_rdev)
        self.tf.add_node('/dev/null', st.st_mode, os.makedev(dev_maj, dev_min))

    # when the string comes from tail() output
    def test_add_string_from_file(self):
        self.copy_strings = []
        testfile = tempfile.NamedTemporaryFile(dir=self.tmpdir, delete=False)
        testfile.write(b"*" * 1000)
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
        self.tf.add_file('tests/unittests/ziptest', dest='tests/unittests/ziptest_renamed')
        self.tf.finalize('auto')

        self.check_for_file('test/tests/unittests/ziptest_renamed')

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
        """Test that re-writing a file with add_string() modifies the content.
        """
        self.tf.add_string('this is my content', 'tests/string_test.txt')
        self.tf.add_string('this is my new content', 'tests/string_test.txt')

        afp = self.tf.open_file('tests/string_test.txt')
        self.assertEquals('this is my new content', afp.read())

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
