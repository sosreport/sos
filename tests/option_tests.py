#!/usr/bin/env python

import unittest

from sos.plugins import Plugin

class GlobalOptionTest(unittest.TestCase):

    def setUp(self):
        self.commons = {
            'global_plugin_options': {
                'test_option': 'foobar',
            },
        }
        self.plugin = Plugin(self.commons)

    def test_simple_lookup(self):
        self.assertEquals(self.plugin.getOption('test_option'), 'foobar')

    def test_multi_lookup(self):
        self.assertEquals(self.plugin.getOption(('not_there', 'test_option')), 'foobar')

if __name__ == "__main__":
    unittest.main()
