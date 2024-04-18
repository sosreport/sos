# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import unittest


from sos.report.plugins import import_plugin, PluginOpt
from sos.utilities import ImporterHelper


class PluginConformance(unittest.TestCase):

    def setUp(self):
        # get all plugin classes defined locally
        import sos.report.plugins
        self.plugs = []
        self.plug_classes = []
        helper = ImporterHelper(sos.report.plugins)
        self.plugs = helper.get_modules()
        for plug in self.plugs:
            self.plug_classes.extend(import_plugin(plug))

    def test_plugin_tuples_set_correctly(self):
        for plug in self.plug_classes:
            for tup in ['packages', 'commands', 'files', 'profiles',
                        'kernel_mods', 'containers']:
                _attr = getattr(plug, tup)
                self.assertIsInstance(
                    _attr, tuple,
                    f"{plug.__name__}.{tup} is type {type(_attr)}"
                )

    def test_plugin_description_is_str(self):
        for plug in self.plug_classes:
            self.assertIsInstance(plug.short_desc, str,
                                  f"{plug.__name__} name not string")
            # make sure the description is not empty
            self.assertNotEqual(plug.short_desc, '',
                                f"{plug.__name__} description unset")

    def test_plugin_name_is_str(self):
        for plug in self.plug_classes:
            self.assertIsInstance(plug.plugin_name, str,
                                  f"{plug.__name__} name not string")
            self.assertNotEqual(plug.plugin_name, '',
                                f"{plug.__name__} name unset")

    def test_plugin_option_list_correct(self):
        for plug in self.plug_classes:
            self.assertIsInstance(plug.option_list, list)
            for opt in plug.option_list:
                self.assertIsInstance(opt, PluginOpt)
                self.assertFalse(opt.name == 'undefined')

    def test_plugin_architectures_set_correctly(self):
        for plug in self.plug_classes:
            self.assertIsInstance(plug.architectures, (tuple, type(None)))
