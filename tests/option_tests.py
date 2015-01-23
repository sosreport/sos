#!/usr/bin/env python

import unittest

from sos.plugins import Plugin

class GlobalOptionTest(unittest.TestCase):

    def setUp(self):
        self.commons = {
            'sysroot': '/',
            'global_plugin_options': {
                'test_option': 'foobar',
                'baz': None,
                'empty_global': True
            },
        }
        self.plugin = Plugin(self.commons)
        self.plugin.opt_names = ['baz', 'empty']
        self.plugin.opt_parms = [{'enabled': False}, {'enabled': None}]

    def test_simple_lookup(self):
        self.assertEquals(self.plugin.get_option('test_option'), 'foobar')

    def test_multi_lookup(self):
        self.assertEquals(self.plugin.get_option(('not_there', 'test_option')), 'foobar')

    def test_cascade(self):
        self.assertEquals(self.plugin.get_option(('baz')), False)

    def test_none_should_cascade(self):
        self.assertEquals(self.plugin.get_option(('empty', 'empty_global')), True)

if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
