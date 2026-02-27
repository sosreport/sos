# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class CryptSetup(Plugin, IndependentPlugin):
    """
    This plugin will capture infromation about the encrypted devices
    that exist on this system.

    Currently, it will only grab /etc/crypttab
    """

    short_desc = 'cryptsetup related files'

    plugin_name = 'cryptsetup'
    profiles = ('hardware', 'storage')
    packages = ('cryptsetup',)

    def setup(self):
        self.add_copy_spec([
            "/etc/crypttab",
        ])

# vim: set et ts=4 sw=4 :
