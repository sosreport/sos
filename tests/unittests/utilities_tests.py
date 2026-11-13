# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os.path
import shutil
import signal
import tempfile
import threading
import time
import unittest

# PYCOMPAT
from io import StringIO

from sos.utilities import (grep, is_executable, sos_get_command_output,
                           find, tail, shell_out, tac_logs, StdinWriter,
                           SoSTimeoutError)

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


class CommandTimeoutTest(unittest.TestCase):
    """Ensure that command timeouts and plugin timeouts are handled
    separately, and that a child of a timed out command which keeps stdout
    open cannot block sos_get_command_output()
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.pidfile = os.path.join(self.tmpdir, 'pid')
        # leaves behind a child that holds stdout open after the timeout
        self.belford = (f"sh -c 'echo partial; sleep 10 & "
                        f"echo $! > {self.pidfile}; exec sleep 10'")

    def tearDown(self):
        pid = self._get_pid()
        if pid and self._is_alive(pid):
            os.kill(pid, signal.SIGKILL)
        shutil.rmtree(self.tmpdir)

    def _get_pid(self):
        try:
            with open(self.pidfile, 'r', encoding='utf-8') as pfile:
                return int(pfile.read())
        except (OSError, ValueError):
            return None

    @staticmethod
    def _is_alive(pid):
        try:
            with open(f"/proc/{pid}/stat", 'r', encoding='utf-8') as stat:
                return stat.read().rsplit(')', 1)[1].split()[0] != 'Z'
        except OSError:
            return False

    def _assert_exits(self, pid, wait=5):
        for _ in range(wait * 10):
            if not self._is_alive(pid):
                return
            time.sleep(0.1)
        self.fail(f"process {pid} is still running")

    def test_cmd_timeout_returns_status(self):
        result = sos_get_command_output('sleep 10', timeout=1,
                                        poller=lambda: False)
        self.assertEqual(result['status'], 124)

    def test_plugin_timeout_raises(self):
        with self.assertRaises(SoSTimeoutError):
            sos_get_command_output('sleep 10', timeout=30,
                                   poller=lambda: True)

    def test_cmd_timeout_with_lingering_child(self):
        start = time.time()
        result = sos_get_command_output(self.belford, timeout=1,
                                        foreground=True,
                                        poller=lambda: False)
        self.assertEqual(result['status'], 124)
        self.assertEqual(result['output'], 'partial\n')
        self.assertLess(time.time() - start, 5)

    def test_cmd_timeout_with_lingering_child_no_poller(self):
        # exiting with 124 is what the timeout command does, and ensures it
        # exits before sos stops waiting on it
        cmd = (f"sh -c 'echo partial; sleep 10 & echo $! > {self.pidfile}; "
               "exit 124'")
        start = time.time()
        result = sos_get_command_output(cmd, timeout=30, foreground=True)
        self.assertEqual(result['status'], 124)
        self.assertEqual(result['output'], 'partial\n')
        self.assertLess(time.time() - start, 5)

    def test_cmd_timeout_with_lingering_child_to_file(self):
        outfile = os.path.join(self.tmpdir, 'output')
        start = time.time()
        result = sos_get_command_output(self.belford, timeout=1,
                                        foreground=True,
                                        poller=lambda: False,
                                        to_file=outfile, sizelimit=25)
        self.assertEqual(result['status'], 124)
        self.assertLess(time.time() - start, 5)
        with open(outfile, 'r', encoding='utf-8') as ofile:
            self.assertEqual(ofile.read(), 'partial\n')

    def test_plugin_timeout_with_lingering_child(self):
        start = time.time()
        with self.assertRaises(SoSTimeoutError):
            sos_get_command_output(self.belford, timeout=30, foreground=True,
                                   poller=lambda: time.time() - start > 1)
        self.assertLess(time.time() - start, 5)

    def test_abandoned_reader_closes_pipe(self):
        # the lingering child only writes once the reader is abandoned, and
        # should then be stopped by the closed pipe
        cmd = (f"sh -c 'echo partial; (sleep 2; exec yes) & "
               f"echo $! > {self.pidfile}; exec sleep 10'")
        sos_get_command_output(cmd, timeout=1, foreground=True,
                               poller=lambda: False)
        self._assert_exits(self._get_pid())

    def test_cmd_timeout_kills_cmd_ignoring_termination(self):
        cmd = (f"sh -c 'trap \"\" TERM; echo $$ > {self.pidfile}; "
               "exec sleep 10'")
        for foreground in (False, True):
            start = time.time()
            result = sos_get_command_output(cmd, timeout=1,
                                            foreground=foreground,
                                            poller=lambda: False)
            self.assertEqual(result['status'], 124)
            self.assertLess(time.time() - start, 5)
            self._assert_exits(self._get_pid(), wait=1)

    def test_plugin_timeout_kills_cmd_ignoring_termination(self):
        cmd = (f"sh -c 'trap \"\" TERM; echo $$ > {self.pidfile}; "
               "exec sleep 10'")
        start = time.time()
        with self.assertRaises(SoSTimeoutError):
            sos_get_command_output(cmd, timeout=30,
                                   poller=lambda: time.time() - start > 1)
        self._assert_exits(self._get_pid(), wait=1)

    def test_plugin_timeout_after_sizelimit_reached(self):
        # the reader stops at the sizelimit while the command keeps running
        cmd = "sh -c 'head -c 2097152 /dev/zero; exec sleep 10'"
        start = time.time()
        with self.assertRaises(SoSTimeoutError):
            sos_get_command_output(cmd, timeout=30, binary=True,
                                   to_file=os.path.join(self.tmpdir, 'out'),
                                   sizelimit=1,
                                   poller=lambda: time.time() - start > 1)
        self.assertLess(time.time() - start, 5)

    def test_stdin_held_by_lingering_child(self):
        # the child never reads stdin, so the write cannot complete
        cmd = (f"sh -c 'sleep 10 <&0 >/dev/null 2>&1 & "
               f"echo $! > {self.pidfile}'")
        start = time.time()
        result = sos_get_command_output(cmd, timeout=30,
                                        stdin=b'x' * 1048576)
        self.assertEqual(result['status'], 0)
        self.assertLess(time.time() - start, 5)


class CommandSizelimitTest(unittest.TestCase):

    def test_output_tailed_to_sizelimit(self):
        result = sos_get_command_output(
            "sh -c 'head -c 3145728 /dev/zero; printf end'", binary=True,
            sizelimit=1)
        self.assertEqual(len(result['output']), 1048576)
        self.assertTrue(result['output'].endswith(b'end'))
        self.assertTrue(result['truncated'])

    def test_output_at_sizelimit_not_truncated(self):
        result = sos_get_command_output("head -c 1048576 /dev/zero",
                                        binary=True, sizelimit=1)
        self.assertEqual(len(result['output']), 1048576)
        self.assertFalse(result['truncated'])

# vim: set et ts=4 sw=4 :
