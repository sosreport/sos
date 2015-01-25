import os.path
import unittest

# PYCOMPAT
import six
from six import StringIO

from sos.utilities import grep, get_hash_name, is_executable, sos_get_command_output, find, tail, shell_out
import sos

TEST_DIR = os.path.dirname(__file__)

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

    def test_grep_multiple_files(self):
        matches = grep(".*unittest$", __file__.replace(".pyc", ".py"), "does_not_exist.txt")
        self.assertEquals(matches, ['import unittest\n'])


class TailTest(unittest.TestCase):

    def test_tail(self):
        t = tail("tests/tail_test.txt", 10)
        self.assertEquals(t, six.b("last line\n"))

    def test_tail_too_many(self):
        t = tail("tests/tail_test.txt", 200)
        expected = open("tests/tail_test.txt", "r").read()
        self.assertEquals(t, six.b(expected))


class ExecutableTest(unittest.TestCase):

    def test_nonexe_file(self):
        path = os.path.join(TEST_DIR, 'utility_tests.py')
        self.assertFalse(is_executable(path))

    def test_exe_file(self):
        path = os.path.join(TEST_DIR, 'test_exe.py')
        self.assertTrue(is_executable(path))

    def test_exe_file_abs_path(self):
        self.assertTrue(is_executable("/usr/bin/timeout"))

    def test_output(self):
        path = os.path.join(TEST_DIR, 'test_exe.py')
        result = sos_get_command_output(path)
        self.assertEquals(result['status'], 0)
        self.assertEquals(result['output'], "executed\n")

    def test_output_non_exe(self):
        path = os.path.join(TEST_DIR, 'utility_tests.py')
        result = sos_get_command_output(path)
        self.assertEquals(result['status'], 127)
        self.assertEquals(result['output'], "")

    def test_output_chdir(self):
        cmd = "/bin/bash -c 'echo $PWD'"
        result = sos_get_command_output(cmd, chdir=TEST_DIR)
        print(result)
        self.assertEquals(result['status'], 0)
        self.assertEquals(result['output'].strip(), TEST_DIR)

    def test_shell_out(self):
        path = os.path.join(TEST_DIR, 'test_exe.py')
        self.assertEquals("executed\n", shell_out(path))


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
