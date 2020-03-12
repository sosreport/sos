# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import unittest

from sos.plugins import Plugin
from sos.policies import LinuxPolicy, InitSystem


class MockOptions(object):
    all_logs = False
    dry_run = False
    log_size = 25
    allow_system_changes = False


class GlobalOptionTest(unittest.TestCase):

    def setUp(self):
        self.commons = {
            'sysroot': '/',
            'policy': LinuxPolicy(init=InitSystem()),
            'cmdlineopts': MockOptions()
        }
        self.plugin = Plugin(self.commons)
        self.plugin.opt_names = ['baz', 'empty', 'test_option']
        self.plugin.opt_parms = [
            {'enabled': False}, {'enabled': None}, {'enabled': 'foobar'}
        ]

    def test_simple_lookup(self):
        self.assertEquals(self.plugin.get_option('test_option'), 'foobar')

    def test_cascade(self):
        self.assertEquals(self.plugin.get_option(('baz')), False)


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
