# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import lzma
import unittest
import os
import tarfile
import tempfile
import shutil
from unittest import mock

from sos.archive import TarFileArchive
from sos.utilities import tail, BlockXZFile
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

    def test_make_link(self):
        self.tf.add_file('tests/ziptest')
        self.tf.add_link('tests/ziptest', 'link_name')

        self.tf.finalize('auto')
        self.check_for_file('test/link_name')

    def test_compress(self):
        self.tf.finalize("auto")

    def _xz_blocks(self, path):
        """How many blocks the one xz stream at ``path`` has"""
        with open(path, 'rb') as packed:
            data = packed.read()
        stream = lzma.LZMADecompressor()
        stream.decompress(data)
        self.assertTrue(stream.eof)
        self.assertEqual(stream.unused_data, b'')
        size = (int.from_bytes(data[-8:-4], 'little') + 1) * 4
        return BlockXZFile._read_number(data[-12 - size:-12], 1)[0]

    def test_xz_is_one_block_below_the_block_size(self):
        self.tf.add_file('tests/unittests/ziptest')
        self.tf.finalize('auto')
        self.check_for_file('test/tests/unittests/ziptest')
        self.assertEqual(
            self._xz_blocks(os.path.join(self.tmpdir, 'test.tar.xz')), 1)

    def test_xz_in_blocks_is_read_as_any_archive(self):
        self.tf.add_file('tests/unittests/ziptest')
        with mock.patch('sos.archive.BlockXZFile.BLOCK', 1024):
            self.tf.finalize('auto')
        self.check_for_file('test/tests/unittests/ziptest')
        self.assertGreater(
            self._xz_blocks(os.path.join(self.tmpdir, 'test.tar.xz')), 1)
        with tarfile.open(os.path.join(self.tmpdir, 'test.tar.xz'),
                          mode='r|xz') as rtf:
            self.assertIn('test/tests/unittests/ziptest', rtf.getnames())

    def test_xz_is_compressed_on_the_threads_of_the_archive(self):
        enc = {'encrypt': False}
        for threads, used in ((4, 4), (1, 1), (None, 1)):
            workdir = tempfile.mkdtemp(dir=self.tmpdir)
            archive = TarFileArchive('gibson', workdir, Policy(), threads,
                                     enc, '/')
            self.assertEqual(archive.xz_threads, used)
            archive.add_string('hack the planet', 'motd')
            with mock.patch('sos.archive.BlockXZFile',
                            wraps=BlockXZFile) as packed:
                archive.finalize('xz')
            packed.assert_called_once_with(
                os.path.join(workdir, 'gibson.tar.xz'), used, preset=3)
        # and on as many as whoever finalizes it says
        self.tf.xz_threads = 7
        with mock.patch('sos.archive.BlockXZFile',
                        wraps=BlockXZFile) as packed:
            self.tf.finalize('auto')
        self.assertEqual(packed.call_args[0][1], 7)

    def test_gzip_and_plain_archives_are_written_by_tarfile(self):
        enc = {'encrypt': False}
        for method, suffix in (('gzip', '.tar.gz'), ('none', '.tar')):
            workdir = tempfile.mkdtemp(dir=self.tmpdir)
            archive = TarFileArchive('gibson', workdir, Policy(), 4, enc,
                                     '/')
            archive.add_file('tests/unittests/ziptest')
            with mock.patch('sos.archive.BlockXZFile') as packed:
                archive.finalize(method)
            packed.assert_not_called()
            with tarfile.open(os.path.join(workdir,
                                           f"gibson{suffix}")) as rtf:
                rtf.getmember('gibson/tests/unittests/ziptest')


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
