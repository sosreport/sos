# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Multipath(Plugin, IndependentPlugin):

    short_desc = 'Device-mapper multipath tools'

    plugin_name = 'multipath'
    profiles = ('system', 'storage', 'hardware')

    def setup(self):

        self.add_cmd_tags({
            'multipath -v4 -ll': 'insights_multipath__v4__ll'
        })

        self.add_copy_spec("/etc/multipath.conf", tags='multipath_conf')
        self.add_copy_spec("/etc/multipath/")

        self.add_cmd_output([
            "multipath -ll",
            "multipath -v4 -ll",
            "multipath -t",
            "multipathd show config"
        ])


# vim: set et ts=4 sw=4 :
