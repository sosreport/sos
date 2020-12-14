# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, IndependentPlugin, SoSPredicate)


class ufw(Plugin, IndependentPlugin):

    short_desc = 'Uncomplicated FireWall'

    plugin_name = 'ufw'
    profiles = ('system', 'network')
    packages = ('ufw',)

    def setup(self):
        self.add_copy_spec([
            "/etc/ufw",
            "/var/log/ufw.Log"
        ])

        ufw_pred = SoSPredicate(self, kmods=['bpfilter', 'iptable_filter'],
                                required={'kmods': 'all'})

        self.add_cmd_output([
            "ufw status numbered",
            "ufw app list"
        ], pred=ufw_pred)

# vim: set et ts=4 sw=4 :
