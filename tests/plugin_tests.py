import unittest
import os
import tempfile

# PYCOMPAT
import six
try:
    from StringIO import StringIO
except:
    from io import StringIO

from sos.plugins import Plugin, regex_findall, _mangle_command
from sos.archive import TarFileArchive
import sos.policies

PATH = os.path.dirname(__file__)

def j(filename):
    return os.path.join(PATH, filename)

def create_file(size):
   f = tempfile.NamedTemporaryFile(delete=False)
   f.write(six.b("*" * size * 1024 * 1024))
   f.flush()
   f.close()
   return f.name

class MockArchive(TarFileArchive):

    def __init__(self):
        self.m = {}
        self.strings = {}

    def name(self):
        return "mock.archive"

    def add_file(self, src, dest=None):
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

    option_list = [("opt", 'an option', 'fast', None),
                  ("opt2", 'another option', 'fast', False)]

    def setup(self):
        pass


class NamedMockPlugin(Plugin):
    """This plugin has a description."""

    plugin_name = "testing"

    def setup(self):
        pass


class ForbiddenMockPlugin(Plugin):
    """This plugin has a description."""

    plugin_name = "forbidden"

    def setup(self):
        self.add_forbidden_path("tests")


class EnablerPlugin(Plugin):

    def is_installed(self, pkg):
        return self.is_installed


class MockOptions(object):
    pass


class PluginToolTests(unittest.TestCase):

    def test_regex_findall(self):
        test_s = "\n".join(['this is only a test', 'there are only two lines'])
        test_fo = StringIO(test_s)
        matches = regex_findall(r".*lines$", test_fo)
        self.assertEquals(matches, ['there are only two lines'])

    def test_regex_findall_miss(self):
        test_s = "\n".join(['this is only a test', 'there are only two lines'])
        test_fo = StringIO(test_s)
        matches = regex_findall(r".*not_there$", test_fo)
        self.assertEquals(matches, [])

    def test_regex_findall_bad_input(self):
        matches = regex_findall(r".*", None)
        self.assertEquals(matches, [])
        matches = regex_findall(r".*", [])
        self.assertEquals(matches, [])
        matches = regex_findall(r".*", 1)
        self.assertEquals(matches, [])

    def test_mangle_command(self):
        name_max = 255
        self.assertEquals("foo", _mangle_command("/usr/bin/foo", name_max))
        self.assertEquals("foo_-x", _mangle_command("/usr/bin/foo -x", name_max))
        self.assertEquals("foo_--verbose", _mangle_command("/usr/bin/foo --verbose", name_max))
        self.assertEquals("foo_.path.to.stuff", _mangle_command("/usr/bin/foo /path/to/stuff", name_max))
        longcmd ="foo is " + "a" * 256 + " long_command"
        expected = longcmd[0:name_max].replace(' ', '_')
        self.assertEquals(expected, _mangle_command(longcmd, name_max))


class PluginTests(unittest.TestCase):

    sysroot = os.getcwd()

    def setUp(self):
        self.mp = MockPlugin({
            'cmdlineopts': MockOptions(),
            'sysroot': self.sysroot
        })
        self.mp.archive = MockArchive()

    def test_plugin_default_name(self):
        p = MockPlugin({'sysroot': self.sysroot})
        self.assertEquals(p.name(), "mockplugin")

    def test_plugin_set_name(self):
        p = NamedMockPlugin({'sysroot': self.sysroot})
        self.assertEquals(p.name(), "testing")

    def test_plugin_no_descrip(self):
        p = MockPlugin({'sysroot': self.sysroot})
        self.assertEquals(p.get_description(), "<no description available>")

    def test_plugin_no_descrip(self):
        p = NamedMockPlugin({'sysroot': self.sysroot})
        self.assertEquals(p.get_description(), "This plugin has a description.")

    def test_set_plugin_option(self):
        p = MockPlugin({'sysroot': self.sysroot})
        p.set_option("opt", "testing")
        self.assertEquals(p.get_option("opt"), "testing")

    def test_set_nonexistant_plugin_option(self):
        p = MockPlugin({'sysroot': self.sysroot})
        self.assertFalse(p.set_option("badopt", "testing"))

    def test_get_nonexistant_plugin_option(self):
        p = MockPlugin({'sysroot': self.sysroot})
        self.assertEquals(p.get_option("badopt"), 0)

    def test_get_unset_plugin_option(self):
        p = MockPlugin({'sysroot': self.sysroot})
        self.assertEquals(p.get_option("opt"), 0)

    def test_get_unset_plugin_option_with_default(self):
        # this shows that even when we pass in a default to get,
        # we'll get the option's default as set in the plugin
        # this might not be what we really want
        p = MockPlugin({'sysroot': self.sysroot})
        self.assertEquals(p.get_option("opt", True), True)

    def test_get_unset_plugin_option_with_default_not_none(self):
        # this shows that even when we pass in a default to get,
        # if the plugin default is not None
        # we'll get the option's default as set in the plugin
        # this might not be what we really want
        p = MockPlugin({'sysroot': self.sysroot})
        self.assertEquals(p.get_option("opt2", True), False)

    def test_get_option_as_list_plugin_option(self):
        p = MockPlugin({'sysroot': self.sysroot})
        p.set_option("opt", "one,two,three")
        self.assertEquals(p.get_option_as_list("opt"), ['one', 'two', 'three'])

    def test_get_option_as_list_plugin_option_default(self):
        p = MockPlugin({'sysroot': self.sysroot})
        self.assertEquals(p.get_option_as_list("opt", default=[]), [])

    def test_get_option_as_list_plugin_option_not_list(self):
        p = MockPlugin({'sysroot': self.sysroot})
        p.set_option("opt", "testing")
        self.assertEquals(p.get_option_as_list("opt"), ['testing'])

    def test_copy_dir(self):
        self.mp._do_copy_path("tests")
        self.assertEquals(self.mp.archive.m["tests/plugin_tests.py"], 'tests/plugin_tests.py')

    def test_copy_dir_bad_path(self):
        self.mp._do_copy_path("not_here_tests")
        self.assertEquals(self.mp.archive.m, {})

    def test_copy_dir_forbidden_path(self):
        p = ForbiddenMockPlugin({
            'cmdlineopts': MockOptions(),
            'sysroot': self.sysroot
        })
        p.archive = MockArchive()
        p.setup()
        p._do_copy_path("tests")
        self.assertEquals(p.archive.m, {})


class AddCopySpecTests(unittest.TestCase):

    expect_paths = set(['tests/tail_test.txt'])

    def setUp(self):
        self.mp = MockPlugin({
            'cmdlineopts': MockOptions(),
            'sysroot': os.getcwd()
        })
        self.mp.archive = MockArchive()

    def assert_expect_paths(self):
        def pathmunge(path):
            if path[0] == '/':
                path = path[1:]
            return os.path.join(self.mp.sysroot, path)
        expected_paths = set(map(pathmunge, self.expect_paths))
        self.assertEquals(self.mp.copy_paths, expected_paths)
        
    # add_copy_spec()

    def test_single_file(self):
        self.mp.add_copy_spec('tests/tail_test.txt')
        self.assert_expect_paths()
    def test_glob_file(self):
        self.mp.add_copy_spec('tests/tail_test.*')
        self.assert_expect_paths()

    def test_single_file_under_limit(self):
        self.mp.add_copy_spec_limit("tests/tail_test.txt", 1)
        self.assert_expect_paths()

    # add_copy_spec_limit()

    def test_single_file_over_limit(self):
        self.mp.sysroot = '/'
        fn = create_file(2) # create 2MB file, consider a context manager
        self.mp.add_copy_spec_limit(fn, 1)
        content, fname = self.mp.copy_strings[0]
        self.assertTrue("tailed" in fname)
        self.assertTrue("tmp" in fname)
        self.assertTrue("/" not in fname)
        self.assertEquals(1024 * 1024, len(content))
        os.unlink(fn)

    def test_bad_filename(self):
        self.mp.sysroot = '/'
        self.assertFalse(self.mp.add_copy_spec_limit('', 1))
        self.assertFalse(self.mp.add_copy_spec_limit(None, 1))

    def test_glob_file_over_limit(self):
        self.mp.sysroot = '/'
        # assume these are in /tmp
        fn = create_file(2)
        fn2 = create_file(2)
        self.mp.add_copy_spec_limit("/tmp/tmp*", 1)
        self.assertEquals(len(self.mp.copy_strings), 1)
        content, fname = self.mp.copy_strings[0]
        self.assertTrue("tailed" in fname)
        self.assertEquals(1024 * 1024, len(content))
        os.unlink(fn)
        os.unlink(fn2)


class CheckEnabledTests(unittest.TestCase):

    def setUp(self):
        self.mp = EnablerPlugin({
            'policy': sos.policies.load(),
            'sysroot': os.getcwd()
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
            'sysroot': os.getcwd()
        })
        self.mp.archive = MockArchive()

    def test_file_never_copied(self):
        self.assertEquals(0, self.mp.do_file_sub("never_copied", r"^(.*)$", "foobar"))

    def test_no_replacements(self):
        self.mp.add_copy_spec(j("tail_test.txt"))
        self.mp.collect()
        replacements = self.mp.do_file_sub(j("tail_test.txt"), r"wont_match", "foobar")
        self.assertEquals(0, replacements)

    def test_replacements(self):
        # test uses absolute paths
        self.mp.sysroot = '/'
        self.mp.add_copy_spec(j("tail_test.txt"))
        self.mp.collect()
        replacements = self.mp.do_file_sub(j("tail_test.txt"), r"(tail)", "foobar")
        self.assertEquals(1, replacements)
        self.assertTrue("foobar" in self.mp.archive.m.get(j('tail_test.txt')))

if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
