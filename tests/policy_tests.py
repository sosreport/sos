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

        self.assertTrue(p.validatePlugin(FauxPlugin))

    def test_redhat(self):
        p = FauxPolicy()
        p.valid_subclasses = [RedHatPlugin]

        self.assertTrue(p.validatePlugin(FauxRedHatPlugin))

    def test_debian(self):
        p = FauxPolicy()
        p.valid_subclasses = [DebianPlugin]

        self.assertTrue(p.validatePlugin(FauxDebianPlugin))

    def test_fails(self):
        p = FauxPolicy()
        p.valid_subclasses = []

        self.assertFalse(p.validatePlugin(FauxDebianPlugin))

    def test_can_import(self):
        self.assertTrue(import_policy('redhat') is not None)

    def test_cant_import(self):
        self.assertTrue(import_policy('notreal') is None)


class PackageManagerTests(unittest.TestCase):

    def setUp(self):
        self.pm = PackageManager()

    def test_default_all_pkgs(self):
        self.assertEquals(self.pm.allPkgs(), {})

    def test_default_all_pkgs_by_name(self):
        self.assertEquals(self.pm.allPkgsByName('doesntmatter'), [])

    def test_default_all_pkgs_by_name_regex(self):
        self.assertEquals(self.pm.allPkgsByNameRegex('.*doesntmatter$'), [])

    def test_default_pkg_by_name(self):
        self.assertEquals(self.pm.pkgByName('foo'), None)

if __name__ == "__main__":
    unittest.main()
