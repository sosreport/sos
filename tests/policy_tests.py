import unittest

from sos.policies import Policy
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

if __name__ == "__main__":
    unittest.main()
