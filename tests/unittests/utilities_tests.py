# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os.path
import tempfile
import unittest

# PYCOMPAT
from io import StringIO

from sos.utilities import (grep, is_executable, sos_get_command_output,
                           find, tail, shell_out, tac_logs)

TEST_DIR = os.path.dirname(__file__)


class GrepTest(unittest.TestCase):

    def test_file_obj(self):
        test_s = "\n".join(
            ['this is only a test', 'there are only two lines'])
        test_fo = StringIO(test_s)
        matches = grep(".*test$", test_fo)
        self.assertEqual(matches, ['this is only a test\n'])

    def test_real_file(self):
        matches = grep(".*unittest$", __file__.replace(".pyc", ".py"))
        self.assertEqual(matches, ['import unittest\n'])

    def test_open_file(self):
        with open(__file__.replace(".pyc", ".py"), encoding='utf-8') as f:
            matches = grep(".*unittest$", f)
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
        with open("tests/unittests/tail_test.txt", "r",
                  encoding='utf-8') as expected:
            self.assertEqual(t, str.encode(expected.read()))


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


class TacTest(unittest.TestCase):

    @staticmethod
    def tac_logs_str(str_src, drop_last_log):
        """Helper to use tac_logs with strings instead of file descriptors"""
        with tempfile.TemporaryFile() as f_src, \
             tempfile.TemporaryFile() as f_dst:
            f_src.write(str_src)
            tac_logs(f_src, f_dst, drop_last_log)
            f_dst.seek(0)
            return f_dst.read()

    def test_tac_limits(self):
        self.assertEqual(self.tac_logs_str(b"", True), b"")
        self.assertEqual(self.tac_logs_str(b"", False), b"")

        self.assertEqual(self.tac_logs_str(b"\n", True), b"")
        self.assertEqual(self.tac_logs_str(b"\n", False), b"\n")

        self.assertEqual(self.tac_logs_str(b"\n\n\n", True), b"\n\n")
        self.assertEqual(self.tac_logs_str(b"\n\n\n", False), b"\n\n\n")

        self.assertEqual(self.tac_logs_str(b" ", True), b"")
        self.assertEqual(self.tac_logs_str(b" ", False), b"")

    def test_tac_partialline(self):
        tac = (b"line 3\n"
               b"line 2\n"
               b"line 1 no new line")

        cat = (b"line 2\n"
               b"line 3\n")

        # partial log line are always dropped
        self.assertEqual(self.tac_logs_str(tac, True), cat)
        self.assertEqual(self.tac_logs_str(tac, False), cat)

    def test_tac_multiline1(self):
        tac = (b"line 5\n"
               b"line 4\n"
               b"multiline 3.0\n"
               b" multiline 3.1\n"
               b" multiline 3.2\n"
               b"line 2\n"
               b"maybe multiline 1.0\n")

        cat1 = (b"line 2\n"
                b"multiline 3.0\n"
                b" multiline 3.1\n"
                b" multiline 3.2\n"
                b"line 4\n"
                b"line 5\n")

        cat2 = (b"maybe multiline 1.0\n"
                b"line 2\n"
                b"multiline 3.0\n"
                b" multiline 3.1\n"
                b" multiline 3.2\n"
                b"line 4\n"
                b"line 5\n")

        self.assertEqual(self.tac_logs_str(tac, True), cat1)
        self.assertEqual(self.tac_logs_str(tac, False), cat2)

    def test_tac_multiline2(self):
        tac = (b"line 3\n"
               b"line 2\n"
               b"multiline 1.0\n"
               b" multiline 1.1\n"
               b" multiline 1.2\n")

        cat1 = (b"line 2\n"
                b"line 3\n")

        cat2 = (b"multiline 1.0\n"
                b" multiline 1.1\n"
                b" multiline 1.2\n"
                b"line 2\n"
                b"line 3\n")

        self.assertEqual(self.tac_logs_str(tac, True), cat1)
        self.assertEqual(self.tac_logs_str(tac, False), cat2)

    def test_tac_multiline_partial(self):
        tac = (b"line 3\n"
               b"line 2\n"
               b"multiline 1.0\n"
               b" multiline 1.1\n"
               b" multiline 1.2")

        cat = (b"line 2\n"
               b"line 3\n")

        self.assertEqual(self.tac_logs_str(tac, True), cat)
        self.assertEqual(self.tac_logs_str(tac, False), cat)

# vim: set et ts=4 sw=4 :
