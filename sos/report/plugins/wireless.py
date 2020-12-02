# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, SoSPredicate


class Wireless(Plugin, IndependentPlugin):

    short_desc = 'Wireless Device Information'

    plugin_name = 'wireless'
    profiles = ('hardware', 'desktop', 'network')
    commands = ('iw', )

    def setup(self):
        wireless_pred = SoSPredicate(self, kmods=['cfg80211'])
        self.add_cmd_output([
            "iw list",
            "iw dev",
            "iwconfig",
            "iwlist scanning"
        ], pred=wireless_pred)

# vim: set et ts=4 sw=4 :
