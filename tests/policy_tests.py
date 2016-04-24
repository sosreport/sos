import unittest

from sos.policies import Policy, PackageManager, import_policy
from sos.plugins import Plugin, IndependentPlugin, RedHatPlugin, DebianPlugin

class FauxPolicy(Policy):
    distro = "Faux"

class FauxPlugin(Plugin, IndependentPlugin):
    pass

class FauxRedHatPlugin(Plugin, RedHatPlugin):
    pass

class FauxDebianPlugin(Plugin, DebianPlugin):
    pass

class PolicyTests(unittest.TestCase):

    def test_independent_only(self):
        p = FauxPolicy()
        p.valid_subclasses = []

        self.assertTrue(p.validate_plugin(FauxPlugin))

    def test_redhat(self):
        p = FauxPolicy()
        p.valid_subclasses = [RedHatPlugin]

        self.assertTrue(p.validate_plugin(FauxRedHatPlugin))

    def test_debian(self):
        p = FauxPolicy()
        p.valid_subclasses = [DebianPlugin]

        self.assertTrue(p.validate_plugin(FauxDebianPlugin))

    def test_fails(self):
        p = FauxPolicy()
        p.valid_subclasses = []

        self.assertFalse(p.validate_plugin(FauxDebianPlugin))

    def test_can_import(self):
        self.assertTrue(import_policy('redhat') is not None)

    def test_cant_import(self):
        self.assertTrue(import_policy('notreal') is None)


class PackageManagerTests(unittest.TestCase):

    def setUp(self):
        self.pm = PackageManager()

    def test_default_all_pkgs(self):
        self.assertEquals(self.pm.all_pkgs(), {})

    def test_default_all_pkgs_by_name(self):
        self.assertEquals(self.pm.all_pkgs_by_name('doesntmatter'), [])

    def test_default_all_pkgs_by_name_regex(self):
        self.assertEquals(self.pm.all_pkgs_by_name_regex('.*doesntmatter$'), [])

    def test_default_pkg_by_name(self):
        self.assertEquals(self.pm.pkg_by_name('foo'), None)

if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
