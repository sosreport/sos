# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos.report.plugins import Plugin, IndependentPlugin


class MvCLI(Plugin, IndependentPlugin):
    """
    The mvCLI plugin is meant for sas adapters, and collects information for
    each adapter discovered on the system.
    """

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

        self.add_cmd_output([f"/opt/marvell/bin/mvcli {s}" for s in subcmds])

# vim: et ts=4 sw=4
