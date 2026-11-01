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
import bz2
import gzip
import lzma
import re

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
        with tarfile.open(os.path.join(self.tmpdir, 'test.tar.xz')) as rtf:
            rtf.getmember(filename)

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
        with tempfile.NamedTemporaryFile(dir=self.tmpdir, delete=False) \
             as testfile:
            testfile.write(b"*" * 1000)
            testfile.flush()

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
        self.tf.add_file('tests/unittests/ziptest',
                         dest='tests/unittests/ziptest_renamed')
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
        self.assertEqual('this is my content', afp.read())

    def test_rewrite_file(self):
        """Test that re-writing a file with add_string() modifies the content.
        """
        self.tf.add_string('this is my content', 'tests/string_test.txt')
        self.tf.add_string('this is my new content', 'tests/string_test.txt')

        afp = self.tf.open_file('tests/string_test.txt')
        self.assertEqual('this is my new content', afp.read())

    def test_substitute_compressed_file(self):
        for compression in (gzip, bz2, lzma):
            with self.subTest(compression=compression.__name__):
                path = os.path.join(
                    self.tmpdir, f'acidburn-{compression.__name__}.log')
                content = b'password=SECRET\nPASSWORD=OTHER\n'
                original = compression.compress(content)
                with open(path, 'wb') as source:
                    source.write(original)
                os.chmod(path, 0o640)
                os.utime(path, (1000000000, 1000000000))
                self.tf.add_file(path)
                replacements = self.tf.do_file_sub(
                    path, re.compile(r'^(password=).*$'), r'\1********')
                self.assertEqual(replacements, 2)
                with open(self.tf.dest_path(path), 'rb') as output:
                    self.assertEqual(
                        compression.decompress(output.read()),
                        b'password=********\nPASSWORD=********\n')
                self.assertEqual(os.stat(self.tf.dest_path(path)).st_mtime,
                                 os.stat(path).st_mtime)
                self.assertEqual(os.stat(self.tf.dest_path(path)).st_mode,
                                 os.stat(path).st_mode)
                with open(path, 'rb') as source:
                    self.assertEqual(source.read(), original)

    def test_substitute_compressed_file_without_matches(self):
        for compression in (gzip, bz2, lzma):
            with self.subTest(compression=compression.__name__):
                path = f'logs/{compression.__name__}.log'
                content = compression.compress(b'nothing sensitive\n')
                self.tf.add_binary(content, path)
                self.assertEqual(self.tf.do_file_sub(
                    path, 'SECRET', '********'), 0)
                with open(self.tf.dest_path(path), 'rb') as output:
                    self.assertEqual(output.read(), content)

    def test_substitute_uncompressed_file_with_compressed_suffix(self):
        self.tf.add_string('password=SECRET\n', 'plain.log.gz')
        self.assertEqual(self.tf.do_file_sub(
            'plain.log.gz', 'SECRET', '********'), 1)
        with self.tf.open_file('plain.log.gz') as output:
            self.assertEqual(output.read(), 'password=********\n')

    def test_substitute_corrupt_compressed_file(self):
        for compression in (gzip, bz2, lzma):
            with self.subTest(compression=compression.__name__):
                path = f'logs/{compression.__name__}.log'
                content = compression.compress(b'password=SECRET\n')[:10]
                self.tf.add_binary(content, path)
                with self.assertRaises(OSError):
                    self.tf.do_file_sub(path, 'SECRET', '********')
                with open(self.tf.dest_path(path), 'rb') as output:
                    self.assertEqual(output.read(), content)

    def test_substitute_invalid_gzip_body(self):
        content = bytearray(gzip.compress(b'password=SECRET\n'))
        content[10] = 0xff
        self.tf.add_binary(content, 'invalid.log.gz')
        with self.assertRaises(OSError):
            self.tf.do_file_sub('invalid.log.gz', 'SECRET', '********')
        with open(self.tf.dest_path('invalid.log.gz'), 'rb') as output:
            self.assertEqual(output.read(), content)

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
