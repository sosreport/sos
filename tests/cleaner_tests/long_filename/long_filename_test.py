# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class LongFilenameTest(Plugin, IndependentPlugin):
    """Fake plugin to test obfuscation of a filename that exceeds NAME_MAX
    once obfuscated
    """

    plugin_name = 'long_filename_test'
    short_desc = 'Fake plugin to test long obfuscated filenames'

    def setup(self):
        self.add_copy_spec('/tmp/sos-test-long-filename/')
