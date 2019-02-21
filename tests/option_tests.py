#!/usr/bin/env python

import unittest

from sos.plugins import Plugin
from sos.policies import LinuxPolicy


class MockOptions(object):
    all_logs = False
    dry_run = False
    log_size = 25


class GlobalOptionTest(unittest.TestCase):

    def setUp(self):
        self.commons = {
            'sysroot': '/',
            'policy': LinuxPolicy(),
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
