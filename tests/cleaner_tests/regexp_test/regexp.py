# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class RegexpTest(Plugin, IndependentPlugin):
    """Test plugin for testing custom regexp obfuscation with --clean
    """

    plugin_name = 'regexp'
    short_desc = 'test plugin for custom regexp obfuscation'

    def setup(self):
        self.add_copy_spec('/tmp/sos-test-regexp.txt')
