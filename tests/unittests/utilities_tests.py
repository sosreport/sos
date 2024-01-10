# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os.path
import unittest

# PYCOMPAT
from io import StringIO

from sos.utilities import (grep, is_executable, sos_get_command_output,
                           find, tail, shell_out)

TEST_DIR = os.path.dirname(__file__)


class GrepTest(unittest.TestCase):

    def test_file_obj(self):
        test_s = u"\n".join(
            ['this is only a test', 'there are only two lines'])
        test_fo = StringIO(test_s)
        matches = grep(".*test$", test_fo)
        self.assertEqual(matches, ['this is only a test\n'])

    def test_real_file(self):
        matches = grep(".*unittest$", __file__.replace(".pyc", ".py"))
        self.assertEqual(matches, ['import unittest\n'])

    def test_open_file(self):
        matches = grep(".*unittest$", open(__file__.replace(".pyc", ".py")))
        self.assertEqual(matches, ['import unittest\n'])

    def test_grep_multiple_files(self):
        matches = grep(".*unittest$",
                       __file__.replace(".pyc", ".py"), "does_not_exist.txt")
        self.assertEqual(matches, ['import unittest\n'])


class TailTest(unittest.TestCase):

    def test_tail(self):
        t = tail("tests/unittests/tail_test.txt", 10)
        self.assertEqual(t, b"last line\n")

    def test_tail_too_many(self):
        t = tail("tests/unittests/tail_test.txt", 200)
        expected = open("tests/unittests/tail_test.txt", "r").read()
        self.assertEqual(t, str.encode(expected))


class ExecutableTest(unittest.TestCase):

    def test_nonexe_file(self):
        path = os.path.join(TEST_DIR, 'utility_tests.py')
        self.assertFalse(is_executable(path))

    def test_exe_file(self):
        self.assertTrue(is_executable('true'))

    def test_exe_file_abs_path(self):
        self.assertTrue(is_executable("/usr/bin/timeout"))

    def test_output(self):
        result = sos_get_command_output("echo executed")
        self.assertEqual(result['status'], 0)
        self.assertEqual(result['output'], "executed\n")

    def test_output_non_exe(self):
        path = os.path.join(TEST_DIR, 'utility_tests.py')
        result = sos_get_command_output(path)
        self.assertEqual(result['status'], 127)
        self.assertEqual(result['output'], b"")

    def test_output_chdir(self):
        cmd = "/bin/bash -c 'echo $PWD'"
        result = sos_get_command_output(cmd, chdir=TEST_DIR)
        self.assertEqual(result['status'], 0)
        self.assertTrue(result['output'].strip().endswith(TEST_DIR))

    def test_shell_out(self):
        self.assertEqual("executed\n", shell_out('echo executed'))


class FindTest(unittest.TestCase):

    def test_find_leaf(self):
        leaves = find("leaf", TEST_DIR)
        self.assertTrue(any(name.endswith("leaf") for name in leaves))

    def test_too_shallow(self):
        leaves = find("leaf", TEST_DIR, max_depth=1)
        self.assertFalse(any(name.endswith("leaf") for name in leaves))

    def test_not_in_pattern(self):
        leaves = find("leaf", TEST_DIR, path_pattern="tests/path")
        self.assertFalse(any(name.endswith("leaf") for name in leaves))

# vim: set et ts=4 sw=4 :
