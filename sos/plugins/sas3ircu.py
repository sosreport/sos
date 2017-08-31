# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


# This sosreport plugin is meant for sas adapters.
# This plugin logs inforamtion on each adapter it finds.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class SAS3ircu(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):

    plugin_name = "sas3ircu"
    commands = ("sas3ircu",)

    def setup(self):

        # get list of adapters
        result = self.call_ext_prog("sas3ircu list", timeout=5)

        if (result["status"] == 0):  # status == 0 means no timeout
            self.add_cmd_output("sas3ircu list",
                                suggest_filename="sas3ircu_list", timeout=5)

            sas_lst = result["output"].splitlines()[10:-1]  # only want devices

            for sas_info in sas_lst:  # for each adapter get some basic info
                sas_num = sas_info.split()[0]
                self.add_cmd_output(
                    "sas3ircu {} display".format(sas_num),
                    suggest_filename="sas3ircu_display_{}".format(sas_num),
                    timeout=5)
                self.add_cmd_output(
                    "sas3ircu {} status".format(sas_num),
                    suggest_filename="sas3ircu_status_{}".format(sas_num),
                    timeout=5)
