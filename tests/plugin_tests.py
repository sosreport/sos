import unittest
import os
import tempfile

# PYCOMPAT
import six
if six.PY2:
    from StringIO import StringIO
else:
    from io import StringIO

from sos.plugins import Plugin, regex_findall, sos_relative_path, mangle_command
from sos.archive import TarFileArchive, ZipFileArchive
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

    profiler = False



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

    def test_rel_path(self):
        path1 = "/usr/lib/foo"
        path2 = "/usr/lib/boo"
        self.assertEquals(sos_relative_path(path1, path2), "../boo")

    def test_abs_path(self):
        path1 = "usr/lib/foo"
        path2 = "foo/lib/boo"
        self.assertEquals(sos_relative_path(path1, path2), "foo/lib/boo")

    def test_bad_path(self):
        path1 = None
        path2 = "foo/lib/boo"
        self.assertEquals(sos_relative_path(path1, path2), "foo/lib/boo")

    def test_mangle_command(self):
        self.assertEquals("foo", mangle_command("/usr/bin/foo"))
        self.assertEquals("foo_-x", mangle_command("/usr/bin/foo -x"))
        self.assertEquals("foo_--verbose", mangle_command("/usr/bin/foo --verbose"))
        self.assertEquals("foo_.path.to.stuff", mangle_command("/usr/bin/foo /path/to/stuff"))
        expected = "foo_.path.to.stuff.this.is.very.long.and.i.only.expect.part.of.it.maybe.this.is.enough.i.hope.so"[0:64]
        self.assertEquals(expected, mangle_command("/usr/bin/foo /path/to/stuff/this/is/very/long/and/i/only/expect/part/of/it/maybe/this/is/enough/i/hope/so"))


class PluginTests(unittest.TestCase):

    def setUp(self):
        self.mp = MockPlugin({
            'cmdlineopts': MockOptions()
        })
        self.mp.archive = MockArchive()

    def test_plugin_default_name(self):
        p = MockPlugin({})
        self.assertEquals(p.name(), "mockplugin")

    def test_plugin_set_name(self):
        p = NamedMockPlugin({})
        self.assertEquals(p.name(), "testing")

    def test_plugin_no_descrip(self):
        p = MockPlugin({})
        self.assertEquals(p.get_description(), "<no description available>")

    def test_plugin_no_descrip(self):
        p = NamedMockPlugin({})
        self.assertEquals(p.get_description(), "This plugin has a description.")

    def test_set_plugin_option(self):
        p = MockPlugin({})
        p.set_option("opt", "testing")
        self.assertEquals(p.get_option("opt"), "testing")

    def test_set_nonexistant_plugin_option(self):
        p = MockPlugin({})
        self.assertFalse(p.set_option("badopt", "testing"))

    def test_get_nonexistant_plugin_option(self):
        p = MockPlugin({})
        self.assertEquals(p.get_option("badopt"), 0)

    def test_get_unset_plugin_option(self):
        p = MockPlugin({})
        self.assertEquals(p.get_option("opt"), 0)

    def test_get_unset_plugin_option_with_default(self):
        # this shows that even when we pass in a default to get,
        # we'll get the option's default as set in the plugin
        # this might not be what we really want
        p = MockPlugin({})
        self.assertEquals(p.get_option("opt", True), True)

    def test_get_unset_plugin_option_with_default_not_none(self):
        # this shows that even when we pass in a default to get,
        # if the plugin default is not None
        # we'll get the option's default as set in the plugin
        # this might not be what we really want
        p = MockPlugin({})
        self.assertEquals(p.get_option("opt2", True), False)

    def test_get_option_as_list_plugin_option(self):
        p = MockPlugin({})
        p.set_option("opt", "one,two,three")
        self.assertEquals(p.get_option_as_list("opt"), ['one', 'two', 'three'])

    def test_get_option_as_list_plugin_option_default(self):
        p = MockPlugin({})
        self.assertEquals(p.get_option_as_list("opt", default=[]), [])

    def test_get_option_as_list_plugin_option_not_list(self):
        p = MockPlugin({})
        p.set_option("opt", "testing")
        self.assertEquals(p.get_option_as_list("opt"), ['testing'])

    def test_copy_dir(self):
        self.mp.do_copy_file_or_dir("tests")
        self.assertEquals(self.mp.archive.m["tests/plugin_tests.py"], 'tests/plugin_tests.py')

    def test_copy_dir_sub(self):
        self.mp.do_copy_file_or_dir("tests", sub=("tests/", "foobar/"))
        self.assertEquals(self.mp.archive.m["tests/plugin_tests.py"], 'foobar/plugin_tests.py')

    def test_copy_dir_bad_path(self):
        self.mp.do_copy_file_or_dir("not_here_tests")
        self.assertEquals(self.mp.archive.m, {})

    def test_copy_dir_forbidden_path(self):
        p = ForbiddenMockPlugin({
            'cmdlineopts': MockOptions()
        })
        p.archive = MockArchive()
        p.setup()
        p.do_copy_file_or_dir("tests")
        self.assertEquals(p.archive.m, {})


class AddCopySpecLimitTests(unittest.TestCase):

    def setUp(self):
        self.mp = MockPlugin({
            'cmdlineopts': MockOptions()
        })
        self.mp.archive = MockArchive()

    def test_single_file_under_limit(self):
        self.mp.add_copy_spec_limit("tests/tail_test.txt", 1)
        self.assertEquals(self.mp.copy_paths, [('tests/tail_test.txt', None)])

    def test_single_file_over_limit(self):
        fn = create_file(2) # create 2MB file, consider a context manager
        self.mp.add_copy_spec_limit(fn, 1, sub=('tmp', 'awesome'))
        content, fname = self.mp.copy_strings[0]
        self.assertTrue("tailed" in fname)
        self.assertTrue("awesome" in fname)
        self.assertTrue("/" not in fname)
        self.assertEquals(1024 * 1024, len(content))
        os.unlink(fn)

    def test_bad_filename(self):
        self.assertFalse(self.mp.add_copy_spec_limit('', 1))
        self.assertFalse(self.mp.add_copy_spec_limit(None, 1))

    def test_glob_file_over_limit(self):
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
        self.mp = EnablerPlugin({'policy': sos.policies.load()})

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
            'cmdlineopts': MockOptions()
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
        self.mp.add_copy_spec(j("tail_test.txt"))
        self.mp.collect()
        replacements = self.mp.do_file_sub(j("tail_test.txt"), r"(tail)", "foobar")
        self.assertEquals(1, replacements)
        self.assertTrue("foobar" in self.mp.archive.m.get(j('tail_test.txt')))

if __name__ == "__main__":
    unittest.main()
