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


class SAS3ircu(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):

    plugin_name = "sas3ircu"
    commands = ("sas3ircu",)

    def setup(self):

        # get list of adapters
        result = self.call_ext_prog("sas3ircu list", timeout=5)

        if (result["status"] == 0):
            self.add_cmd_output("sas3ircu list", timeout=5)

            # only want devices
            sas_lst = result["output"].splitlines()[10:-1]

            # for each adapter get some basic info
            for sas_info in sas_lst:
                sas_num = sas_info.split()[0]
                self.add_cmd_output("sas3ircu %s display" % sas_num, timeout=5)
                self.add_cmd_output("sas3ircu %s status" % sas_num, timeout=5)

# vim: et ts=4 sw=4
