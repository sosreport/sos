# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import unittest

from sos.report.plugins import Plugin, PluginOpt
from sos.policies.distros import LinuxPolicy
from sos.policies.init_systems import InitSystem


class MockOptions(object):
    all_logs = False
    dry_run = False
    log_size = 25
    allow_system_changes = False
    skip_commands = []
    skip_files = []


class MockPlugin(Plugin):

    option_list = [
        PluginOpt('baz', default=False),
        PluginOpt('empty', default=None),
        PluginOpt('test_option', default='foobar')
    ]

    def __init__(self, commons):
        super(MockPlugin, self).__init__(commons=commons)


class GlobalOptionTest(unittest.TestCase):

    def setUp(self):
        self.commons = {
            'sysroot': '/',
            'policy': LinuxPolicy(init=InitSystem()),
            'cmdlineopts': MockOptions(),
            'devices': {}
        }
        self.plugin = MockPlugin(self.commons)

    def test_simple_lookup(self):
        self.assertEquals(self.plugin.get_option('test_option'), 'foobar')

    def test_cascade(self):
        self.assertEquals(self.plugin.get_option(('baz')), False)


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
