# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Snapper(Plugin, IndependentPlugin):

    short_desc = 'System snapper'

    plugin_name = 'snapper'
    commands = ("snapper",)

    def setup(self):

        self.add_cmd_output([
            "snapper --version",
            "snapper list"
        ])

        self.add_dir_listing('/usr/lib/snapper/')

# vim: set et ts=4 sw=4 :
