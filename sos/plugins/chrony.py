# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Chrony(Plugin, RedHatPlugin):
    """Chrony clock (for Network time protocol)
    """

    plugin_name = "chrony"
    profiles = ('system', 'services')

    packages = ('chrony',)

    def setup(self):
        self.add_copy_spec([
            "/etc/chrony.conf",
            "/var/lib/chrony/drift"
        ])
        self.add_cmd_output([
            "chronyc activity",
            "chronyc tracking",
            "chronyc -n sources",
            "chronyc sourcestats",
            "chronyc serverstats",
            "chronyc ntpdata",
            "chronyc -n clients"
        ])
        self.add_journal(units="chronyd")

# vim: et ts=4 sw=4
