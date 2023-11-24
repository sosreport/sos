# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


# This sosreport plugin is meant for sas adapters.
# This plugin logs inforamtion on each adapter it finds.

import re

from sos.report.plugins import Plugin, IndependentPlugin


class arcconf(Plugin, IndependentPlugin):

    short_desc = 'arcconf Integrated RAID adapter information'

    plugin_name = "arcconf"
    commands = ("arcconf",)

    def setup(self):
        # Get the list of available adapters
        listarcconf = self.collect_cmd_output("arcconf list")

        # Parse the 'arcconf list' output and extract controller IDs.
        # For each Controller ID found in 'arcconf list', add commands
        # for getconfig and GETLOGS
        #
        # Sample 'arcconf list' output:
        #
        # Controller information
        # -------------------------------------------------------------
        #    Controller ID   : Status, Slot, Mode, Name, SerialNumber, WWN
        # -------------------------------------------------------------
        #    Controller 1:   : Optimal, Slot XXXX, XXXX, XXXX, XXXX, XXXX
        # -------------------------------------------------------------
        #    Controller 2:   : Optimal, Slot XXXX, XXXX, XXXX, XXXX, XXXX

        if listarcconf['status'] == 0:
            for line in listarcconf['output'].splitlines():
                try:
                    match = re.match(r"^[\s]*Controller (\d)+", line).group(0)
                    controller_id = match.split()[1]
                    if controller_id:
                        # Add new commands with Controller ID
                        self.add_cmd_output([
                            f"arcconf getconfig {controller_id}",
                            f"arcconf GETLOGS {controller_id} UART",
                        ])
                except AttributeError:
                    continue
# vim: et ts=4 sw=4
