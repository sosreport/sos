# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os.path
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock

# PYCOMPAT
from io import StringIO

from sos.utilities import (grep, is_executable, sos_get_command_output,
                           find, tail, shell_out, tac_logs, StdinWriter)

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

    def test_stdin_str(self):
        result = sos_get_command_output('/bin/cat', stdin='hello\n')
        self.assertEqual(result['status'], 0)
        self.assertEqual(result['output'], 'hello\n')

    def test_stdin_bytes(self):
        result = sos_get_command_output('/bin/cat', stdin=b'alpha',
                                        binary=True)
        self.assertEqual(result['status'], 0)
        self.assertEqual(result['output'], b'alpha')

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


class StdinWriterTest(unittest.TestCase):

    def test_write_failure_recorded_as_text(self):
        thread_errors = []

        def collect(args):
            thread_errors.append(args.exc_type)

        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        original_hook = threading.excepthook
        threading.excepthook = collect
        try:
            writer = StdinWriter(os.fdopen(write_fd, 'wb'), b'sos')
            writer.join()
        finally:
            threading.excepthook = original_hook
        self.assertEqual(thread_errors, [])
        self.assertIsInstance(writer.error, str)
        self.assertNotEqual(writer.error, '')


class RunasProfileTest(unittest.TestCase):
    """Test that runas parameter properly loads user profiles"""

    @patch('sos.utilities.is_executable')
    @patch('sos.utilities.pwd.getpwnam')
    def test_runas_uses_runuser_with_login_shell(self, mock_getpwnam,
                                                   mock_is_executable):
        """Test that runas uses runuser -l when available"""
        # Set up mock user
        mock_pwd_user = MagicMock()
        mock_pwd_user.pw_name = 'testuser'
        mock_pwd_user.pw_uid = 1000
        mock_pwd_user.pw_gid = 1000
        mock_pwd_user.pw_dir = '/home/testuser'
        mock_pwd_user.pw_shell = '/bin/bash'
        mock_getpwnam.return_value = mock_pwd_user

        # Mock is_executable to return True for runuser and timeout
        mock_is_executable.side_effect = lambda cmd: cmd in ["runuser",
                                                              "timeout"]

        # We'll patch Popen to capture the command without executing it
        with patch('sos.utilities.Popen') as mock_popen:
            # Set up a minimal mock that won't hang
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.poll.return_value = 0  # Process already finished
            mock_process.stdout.read.return_value = b''  # No output
            mock_process.__enter__ = MagicMock(return_value=mock_process)
            mock_process.__exit__ = MagicMock(return_value=False)
            mock_popen.return_value = mock_process

            # Call with runas parameter
            sos_get_command_output('echo test', runas='testuser',
                                   timeout=0)

            # Verify Popen was called
            self.assertTrue(mock_popen.called)

            # Get the command that was passed to Popen
            call_args = mock_popen.call_args
            command_args = call_args[0][0]  # First positional argument

            # Convert to string for easier checking
            command_str = ' '.join(command_args)

            # The command should contain runuser -l testuser -c
            # 'echo test'
            self.assertIn('runuser', command_str)
            self.assertIn('-l', command_str)
            self.assertIn('testuser', command_str)
            self.assertIn('-c', command_str)
            self.assertIn('echo test', command_str)

    @patch('sos.utilities.is_executable')
    @patch('sos.utilities.pwd.getpwnam')
    def test_runas_uses_su_when_runuser_unavailable(self, mock_getpwnam,
                                                      mock_is_executable):
        """Test that runas falls back to su -l when runuser is not
        available"""
        mock_pwd_user = MagicMock()
        mock_pwd_user.pw_name = 'testuser'
        mock_pwd_user.pw_uid = 1000
        mock_pwd_user.pw_gid = 1000
        mock_pwd_user.pw_dir = '/home/testuser'
        mock_pwd_user.pw_shell = '/bin/bash'
        mock_getpwnam.return_value = mock_pwd_user

        # Mock is_executable: runuser not available, su is available
        def is_exec_side_effect(cmd):
            return cmd in ["su", "timeout"]
        mock_is_executable.side_effect = is_exec_side_effect

        with patch('sos.utilities.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.poll.return_value = 0
            mock_process.stdout.read.return_value = b''
            mock_process.__enter__ = MagicMock(return_value=mock_process)
            mock_process.__exit__ = MagicMock(return_value=False)
            mock_popen.return_value = mock_process

            sos_get_command_output('echo test', runas='testuser',
                                   timeout=0)

            call_args = mock_popen.call_args
            command_args = call_args[0][0]
            command_str = ' '.join(command_args)

            # Should use su instead of runuser
            self.assertIn('su', command_str)
            self.assertIn('-l', command_str)
            self.assertIn('testuser', command_str)
            self.assertIn('-c', command_str)
            self.assertNotIn('runuser', command_str)

    @patch('sos.utilities.is_executable')
    @patch('sos.utilities.pwd.getpwnam')
    def test_runas_quotes_command_properly(self, mock_getpwnam,
                                            mock_is_executable):
        """Test that commands with special characters are properly
        quoted"""
        mock_pwd_user = MagicMock()
        mock_pwd_user.pw_name = 'testuser'
        mock_pwd_user.pw_uid = 1000
        mock_pwd_user.pw_gid = 1000
        mock_pwd_user.pw_dir = '/home/testuser'
        mock_pwd_user.pw_shell = '/bin/bash'
        mock_getpwnam.return_value = mock_pwd_user

        mock_is_executable.side_effect = lambda cmd: cmd in ["runuser",
                                                              "timeout"]

        with patch('sos.utilities.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.poll.return_value = 0
            mock_process.stdout.read.return_value = b''
            mock_process.__enter__ = MagicMock(return_value=mock_process)
            mock_process.__exit__ = MagicMock(return_value=False)
            mock_popen.return_value = mock_process

            # Command with special characters that need quoting
            complex_cmd = 'echo "hello world" && ls -la'
            sos_get_command_output(complex_cmd, runas='testuser',
                                   timeout=0)

            call_args = mock_popen.call_args
            command_args = call_args[0][0]

            # Verify the structure includes runuser and -c
            command_str = ' '.join(command_args)
            self.assertIn('runuser', command_str)
            self.assertIn('-c', command_str)
            # The complex command should be preserved
            self.assertIn('echo', command_str)

# vim: set et ts=4 sw=4 :
