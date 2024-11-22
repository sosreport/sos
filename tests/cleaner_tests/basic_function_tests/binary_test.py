# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class BinaryPlugin(Plugin, IndependentPlugin):
    """Test plugin for testing binary removal with --clean
    """

    plugin_name = 'binary_test'
    short_desc = 'test plugin for removing binaries with --clean'

    def setup(self):
        self.add_copy_spec('/var/log/binary_test.tar.xz')
