# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


# This sosreport plugin is meant for sas adapters.
# This plugin logs inforamtion on each adapter it finds.

from sos.report.plugins import Plugin, IndependentPlugin


class mvCLI(Plugin, IndependentPlugin):

    short_desc = 'mvCLI Integrated RAID adapter information'

    plugin_name = "mvcli"
    commands = ("/opt/marvell/bin/mvcli",)

    def setup(self):

        # get list of adapters
        subcmds = [
            'info -o vd',
            'info -o pd',
            'info -o hba',
            'smart -p 0',
        ]

        self.add_cmd_output(["/opt/marvell/bin/mvcli %s" % s for s in subcmds])

# vim: et ts=4 sw=4
