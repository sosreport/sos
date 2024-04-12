# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import unittest
import os
import tempfile
import shutil
import random

from io import StringIO
from string import ascii_lowercase
from sos.report.plugins import (Plugin, regex_findall,
                                _mangle_command, PluginOpt)
from sos.archive import TarFileArchive
from sos.policies.distros import LinuxPolicy
from sos.policies.init_systems import InitSystem

PATH = os.path.dirname(__file__)


def j(filename):
    return os.path.join(PATH, filename)


def create_file(size, dir=None):
    f = tempfile.NamedTemporaryFile(delete=False, dir=dir, mode='w')
    fsize = size * 1024 * 1024
    content = ''.join(random.choice(ascii_lowercase) for x in range(fsize))
    f.write(content)
    f.flush()
    f.close()
    return f.name


class MockArchive(TarFileArchive):

    def __init__(self):
        self.m = {}
        self.strings = {}

    def name(self):
        return "mock.archive"

    def add_file(self, src, dest=None, force=False):
        if not dest:
            dest = src
        self.m[src] = dest

    def add_string(self, content, dest):
        self.m[dest] = content

    def add_link(self, dest, link_name):
        pass

    def open_file(self, name):
        return open(self.m.get(name), 'r')

    def close(self):
        pass

    def compress(self, method):
        pass


class MockPlugin(Plugin):

    option_list = [
        PluginOpt("opt", default=None, desc='an option', val_type=str),
        PluginOpt("opt2", default=False, desc='another option')
    ]

    def setup(self):
        pass


class NamedMockPlugin(Plugin):

    short_desc = "This plugin has a description."
    plugin_name = "testing"

    def setup(self):
        pass


class PostprocMockPlugin(Plugin):

    did_postproc = False

    def setup(self):
        pass

    def postproc(self):
        if self.get_option('postproc'):
            self.did_postproc = True


class ForbiddenMockPlugin(Plugin):
    """This plugin has a description."""

    plugin_name = "forbidden"

    def setup(self):
        self.add_copy_spec("tests")
        self.add_forbidden_path("tests")


class EnablerPlugin(Plugin):

    def is_installed(self, pkg):
        return self.is_installed


class MockOptions(object):
    all_logs = False
    dry_run = False
    since = None
    log_size = 25
    allow_system_changes = False
    no_postproc = False
    skip_files = []
    skip_commands = []
    sysroot = None


class PluginToolTests(unittest.TestCase):

    def test_regex_findall(self):
        test_s = u"\n".join(
            ['this is only a test', 'there are only two lines'])
        test_fo = StringIO(test_s)
        matches = regex_findall(r".*lines$", test_fo)
        self.assertEqual(matches, ['there are only two lines'])

    def test_regex_findall_miss(self):
        test_s = u"\n".join(
            ['this is only a test', 'there are only two lines'])
        test_fo = StringIO(test_s)
        matches = regex_findall(r".*not_there$", test_fo)
        self.assertEqual(matches, [])

    def test_regex_findall_bad_input(self):
        matches = regex_findall(r".*", None)
        self.assertEqual(matches, [])
        matches = regex_findall(r".*", [])
        self.assertEqual(matches, [])
        matches = regex_findall(r".*", 1)
        self.assertEqual(matches, [])

    def test_mangle_command(self):
        name_max = 255
        self.assertEqual("foo", _mangle_command("/usr/bin/foo", name_max))
        self.assertEqual(
            "foo_-x", _mangle_command("/usr/bin/foo -x", name_max))
        self.assertEqual(
            "foo_--verbose", _mangle_command("/usr/bin/foo --verbose",
                                             name_max))
        self.assertEqual("foo_.path.to.stuff", _mangle_command(
            "/usr/bin/foo /path/to/stuff", name_max))
        longcmd = "foo is " + "a" * 256 + " long_command"
        expected = longcmd[0:name_max].replace(' ', '_')
        self.assertEqual(expected, _mangle_command(longcmd, name_max))


class PluginTests(unittest.TestCase):

    sysroot = os.getcwd()

    def setUp(self):
        self.mp = MockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        self.mp.archive = MockArchive()

    def test_plugin_default_name(self):
        p = MockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        self.assertEqual(p.name(), "mockplugin")

    def test_plugin_set_name(self):
        p = NamedMockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        self.assertEqual(p.name(), "testing")

    def test_plugin_no_descrip(self):
        p = MockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        self.assertEqual(p.get_description(), "<no description available>")

    def test_plugin_has_descrip(self):
        p = NamedMockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        self.assertEqual(p.get_description(),
                         "This plugin has a description.")

    def test_set_plugin_option(self):
        p = MockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        p.set_option("opt", "testing")
        self.assertEqual(p.get_option("opt"), "testing")

    def test_set_nonexistant_plugin_option(self):
        p = MockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        self.assertFalse(p.set_option("badopt", "testing"))

    def test_get_nonexistant_plugin_option(self):
        p = MockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        self.assertEqual(p.get_option("badopt"), 0)

    def test_get_unset_plugin_option(self):
        p = MockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        self.assertEqual(p.get_option("opt"), None)

    def test_get_unset_plugin_option_with_default(self):
        # this shows that even when we pass in a default to get,
        # we'll get the option's default as set in the plugin
        # this might not be what we really want
        p = MockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        self.assertEqual(p.get_option("opt", True), True)

    def test_get_unset_plugin_option_with_default_not_none(self):
        # this shows that even when we pass in a default to get,
        # if the plugin default is not None
        # we'll get the option's default as set in the plugin
        # this might not be what we really want
        p = MockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        self.assertEqual(p.get_option("opt2", True), False)

    def test_copy_dir(self):
        self.mp._do_copy_path("tests")
        self.assertEqual(
            self.mp.archive.m["tests/unittests/plugin_tests.py"],
            'tests/unittests/plugin_tests.py')

    def test_copy_dir_bad_path(self):
        self.mp._do_copy_path("not_here_tests")
        self.assertEqual(self.mp.archive.m, {})

    def test_copy_dir_forbidden_path(self):
        p = ForbiddenMockPlugin({
            'cmdlineopts': MockOptions(),
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'devices': {}
        })
        p.archive = MockArchive()
        p.setup()
        p.collect_plugin()
        self.assertEqual(p.archive.m, {})

    def test_postproc_default_on(self):
        p = PostprocMockPlugin({
            'cmdlineopts': MockOptions(),
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem()),
            'devices': {}
        })
        p.postproc()
        self.assertTrue(p.did_postproc)

    def test_set_default_cmd_env(self):
        p = MockPlugin({
            'sysroot': self.sysroot,
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })
        e = {'TORVALDS': 'Linus'}
        p.set_default_cmd_environment(e)
        self.assertEqual(p.default_environment, e)
        add_e = {'GREATESTSPORT': 'hockey'}
        p.add_default_cmd_environment(add_e)
        self.assertEqual(p.default_environment['GREATESTSPORT'], 'hockey')
        self.assertEqual(p.default_environment['TORVALDS'], 'Linus')


class AddCopySpecTests(unittest.TestCase):

    expect_paths = set(['tests/unittests/tail_test.txt'])

    def setUp(self):
        self.mp = MockPlugin({
            'cmdlineopts': MockOptions(),
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'sysroot': os.getcwd(),
            'devices': {}
        })
        self.mp.archive = MockArchive()

    def assert_expect_paths(self):
        def pathmunge(path):
            if path[0] == '/':
                path = path[1:]
            return os.path.join(self.mp.sysroot, path)
        expected_paths = set(map(pathmunge, self.expect_paths))
        self.assertEqual(self.mp.copy_paths, expected_paths)

    def test_single_file_no_limit(self):
        self.mp.add_copy_spec("tests/unittests/tail_test.txt")
        self.assert_expect_paths()

    def test_single_file_under_limit(self):
        self.mp.add_copy_spec("tests/unittests/tail_test.txt", 1)
        self.assert_expect_paths()

    def test_single_file_over_limit(self):
        self.mp.sysroot = '/'
        fn = create_file(2)  # create 2MB file, consider a context manager
        self.mp.add_copy_spec(fn, 1)
        fname, _size = self.mp._tail_files_list[0]
        self.assertTrue(fname == fn)
        self.assertTrue("tmp" in fname)
        self.assertEqual(1024 * 1024, _size)
        os.unlink(fn)

    def test_bad_filename(self):
        self.mp.sysroot = '/'
        self.assertFalse(self.mp.add_copy_spec('', 1))
        self.assertFalse(self.mp.add_copy_spec(None, 1))

    def test_glob_file(self):
        self.mp.add_copy_spec('tests/unittests/tail_test.*')
        self.assert_expect_paths()

    def test_glob_file_limit_no_limit(self):
        self.mp.sysroot = '/'
        tmpdir = tempfile.mkdtemp()
        create_file(2, dir=tmpdir)
        create_file(2, dir=tmpdir)
        self.mp.add_copy_spec(tmpdir + "/*")
        self.assertEqual(len(self.mp.copy_paths), 2)
        shutil.rmtree(tmpdir)

    def test_glob_file_over_limit(self):
        self.mp.sysroot = '/'
        tmpdir = tempfile.mkdtemp()
        create_file(2, dir=tmpdir)
        create_file(2, dir=tmpdir)
        self.mp.add_copy_spec(tmpdir + "/*", 1)
        self.assertEqual(len(self.mp._tail_files_list), 1)
        fname, _size = self.mp._tail_files_list[0]
        self.assertEqual(1024 * 1024, _size)
        shutil.rmtree(tmpdir)

    def test_multiple_files_no_limit(self):
        self.mp.add_copy_spec([
            'tests/unittests/tail_test.txt',
            'tests/unittests/test.txt',
        ])
        self.assertEqual(len(self.mp.copy_paths), 2)

    def test_multiple_files_under_limit(self):
        self.mp.add_copy_spec([
            'tests/unittests/tail_test.txt',
            'tests/unittests/test.txt',
        ], 1)
        self.assertEqual(len(self.mp.copy_paths), 2)


class CheckEnabledTests(unittest.TestCase):

    def setUp(self):
        self.mp = EnablerPlugin({
            'policy': LinuxPolicy(probe_runtime=False),
            'sysroot': os.getcwd(),
            'cmdlineopts': MockOptions(),
            'devices': {}
        })

    def test_checks_for_file(self):
        f = j("tail_test.txt")
        self.mp.files = (f,)
        self.assertTrue(self.mp.check_enabled())

    def test_checks_for_package(self):
        self.mp.packages = ('foo',)
        self.assertTrue(self.mp.check_enabled())

    def test_allows_bad_tuple(self):
        f = j("tail_test.txt")
        self.mp.files = (f)
        self.mp.packages = ('foo')
        self.assertTrue(self.mp.check_enabled())

    def test_enabled_by_default(self):
        self.assertTrue(self.mp.check_enabled())


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


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
