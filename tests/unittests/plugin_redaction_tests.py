# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import gzip
import os
import shutil
import tempfile
import unittest

from sos.archive import TarFileArchive
from sos.policies.distros import LinuxPolicy
from sos.policies.init_systems import InitSystem
from unittests.plugin_tests import MockArchive, MockOptions, MockPlugin, j


class RegexSubTests(unittest.TestCase):

    def setUp(self):
        self.mp = MockPlugin({
            'cmdlineopts': MockOptions(),
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'sysroot': os.getcwd(),
            'devices': {}
        })
        self.mp.archive = MockArchive()

    def test_file_never_copied(self):
        self.assertEqual(0, self.mp.do_file_sub(
            "never_copied", r"^(.*)$", "foobar"))

    def test_no_replacements(self):
        self.mp.sysroot = '/'
        self.mp.add_copy_spec(j("tail_test.txt"))
        self.mp.collect_plugin()
        replacements = self.mp.do_file_sub(
            j("tail_test.txt"), r"wont_match", "foobar")
        self.assertEqual(0, replacements)

    def test_replacements(self):
        # test uses absolute paths
        self.mp.sysroot = '/'
        self.mp.add_copy_spec(j("tail_test.txt"))
        self.mp.collect_plugin()
        replacements = self.mp.do_file_sub(
            j("tail_test.txt"), r"(tail)", "foobar")
        self.assertEqual(1, replacements)
        self.assertTrue("foobar" in self.mp.archive.m.get(j('tail_test.txt')))

    def test_path_regex_sub_with_sysroot(self):
        # path expressions match the path within the sysroot, which is the
        # path of the file within the archive
        sysroot = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, sysroot)
        os.makedirs(os.path.join(sysroot, 'etc', 'test'))
        collected = {
            'app.conf': 'password=hackers\n',
            'key.pem': '-----BEGIN PRIVATE KEY-----\nhackers\n'
                       '-----END PRIVATE KEY-----\n',
        }
        for name, content in collected.items():
            with open(os.path.join(sysroot, 'etc', 'test', name), 'w',
                      encoding='utf-8') as tfile:
                tfile.write(content)
        # MockArchive cannot read back a file collected from a sysroot
        archive_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, archive_dir)
        self.mp.archive = TarFileArchive('test', archive_dir, self.mp.policy,
                                         1, {'encrypt': False}, sysroot)
        self.mp.sysroot = sysroot
        self.mp.add_copy_spec('/etc/test/')
        self.mp.collect_plugin()
        self.mp.do_path_regex_sub(r'/etc/test/.*\.conf', r'(password=)\S+',
                                  r'\1******')
        self.mp.do_file_private_sub(r'/etc/test/.*\.pem')
        scrubbed = {
            'app.conf': 'password=******\n',
            'key.pem': '-----SCRUBBED PRIVATE KEY-----\n',
        }
        for name, content in scrubbed.items():
            path = os.path.join(self.mp.archive.get_archive_path(), 'etc',
                                'test', name)
            with open(path, encoding='utf-8') as afile:
                self.assertEqual(afile.read(), content)

    def test_compressed_path_replacements(self):
        self.mp.sysroot = '/'
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'rotated.log.gz')
            with gzip.open(src, 'wt') as source:
                source.write('password=SECRET\n')
            self.mp.archive = TarFileArchive(
                'report', tmpdir, self.mp.policy, 1, {'encrypt': False}, '/')
            self.mp.add_copy_spec(src)
            self.mp.collect_plugin()
            self.mp.do_path_regex_sub(src, r'(password=).*', r'\1********')
            with gzip.open(self.mp.archive.dest_path(src), 'rt') as output:
                self.assertEqual(output.read(), 'password=********\n')

    def test_compressed_limit_blocks_final_archive(self):
        self.mp.sysroot = '/'
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'rotated.log.gz')
            with gzip.open(src, 'wt') as source:
                source.write('password=SECRET\n')
            self.mp.archive = TarFileArchive(
                'report', tmpdir, self.mp.policy, 1, {'encrypt': False}, '/')
            self.mp.archive._substitution_limit = 8
            self.mp.add_copy_spec(src)
            self.mp.collect_plugin()
            self.mp.do_path_regex_sub(src, r'(password=).*', r'\1********')
            with self.assertRaises(OSError):
                self.mp.archive.finalize('gzip')
            self.assertFalse(os.path.exists(
                self.mp.archive.get_archive_path() + '.tar.gz'))
            with gzip.open(src, 'rt') as source:
                self.assertEqual(source.read(), 'password=SECRET\n')
