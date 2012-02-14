#!/usr/bin/env python

import unittest

from sos.plugins import Plugin

class GlobalOptionTest(unittest.TestCase):

    def setUp(self):
        self.commons = {
            'global_plugin_options': {
                'test_option': 'foobar',
                'baz': None,
                'empty_global': True,
            },
        }
        self.plugin = Plugin(self.commons)
        self.plugin.optNames = ['baz', 'empty']
        self.plugin.optParms = [{'enabled': False}, {'enabled': None}]

    def test_simple_lookup(self):
        self.assertEquals(self.plugin.getOption('test_option'), 'foobar')

    def test_multi_lookup(self):
        self.assertEquals(self.plugin.getOption(('not_there', 'test_option')), 'foobar')

    def test_cascade(self):
        self.assertEquals(self.plugin.getOption(('baz')), False)

    def test_none_should_cascade(self):
        self.assertEquals(self.plugin.getOption(('empty', 'empty_global')), True)

if __name__ == "__main__":
    unittest.main()
