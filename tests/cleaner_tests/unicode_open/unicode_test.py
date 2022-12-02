# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class UnicodeTest(Plugin, IndependentPlugin):
    """Fake plugin to test the handling of a file with embedded unicode
    """

    plugin_name = 'unicode_test'
    short_desc = 'Fake plugin to test unicode file handling'

    def setup(self):
        self.add_copy_spec('/tmp/sos-test-unicode.txt')
