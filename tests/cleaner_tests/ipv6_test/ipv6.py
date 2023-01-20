# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class IPv6(Plugin, IndependentPlugin):
    """Collect arbitrary file containing crafted ipv6 adresses to test ipv6
    obfuscation.
    """

    plugin_name = 'ipv6'
    short_desc = 'fake plugin to test ipv6 obfuscation'

    def setup(self):
        self.add_copy_spec([
            '/tmp/sos-test-ipv6.txt',
        ])
