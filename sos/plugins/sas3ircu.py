# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


# This sosreport plugin is meant for sas adapters.
# This plugin logs inforamtion on each adapter it finds.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class SAS3ircu(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """SAS-3 Integrated RAID adapter information
    """

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
