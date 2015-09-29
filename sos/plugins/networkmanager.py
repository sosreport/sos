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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
import os


class NetworkManager(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """NetworkManager commands and service information
    """
    plugin_name = "networkmanager"
    profiles = ('network', 'system')

    def setup(self):
        super(NetworkManager, self).setup()
        self.add_copy_spec([
            "/etc/NetworkManager/NetworkManager.conf",
            "/etc/NetworkManager/system-connections"
        ])

        # There are some incompatible changes in nmcli since
        # the release of NetworkManager >= 0.9.9. In addition,
        # NetworkManager >= 0.9.9 will use the long names of
        # "nmcli" objects.

        # All versions conform to the following templates with differnt
        # strings for the object being operated on.
        nmcli_con_details_template = "nmcli con %s id"
        nmcli_dev_details_template = "nmcli dev %s"

        # test NetworkManager status for the specified major version
        def test_nm_status(version=1):
            status_template = "nmcli --terse --fields RUNNING %s status"
            obj_table = [
                "nm",        # <  0.9.9
                "general"    # >= 0.9.9
            ]
            status = self.call_ext_prog(status_template % obj_table[version])
            return status['output'].lower().startswith("running")

        # NetworkManager >= 0.9.9 (Use short name of objects for nmcli)
        if test_nm_status(version=1):
            self.add_cmd_output([
                "nmcli general status",
                "nmcli con",
                "nmcli con show --active",
                "nmcli dev"])
            nmcli_con_details_cmd = nmcli_con_details_template % "show"
            nmcli_dev_details_cmd = nmcli_dev_details_template % "show"

        # NetworkManager < 0.9.9 (Use short name of objects for nmcli)
        elif test_nm_status(version=0):
            self.add_cmd_output([
                "nmcli nm status",
                "nmcli con",
                "nmcli con status",
                "nmcli dev"])
            nmcli_con_details_cmd = nmcli_con_details_template % "list id"
            nmcli_dev_details_cmd = nmcli_dev_details_template % "list iface"

        # No grokkable NetworkManager version present
        else:
            nmcli_con_details_cmd = ""
            nmcli_dev_details_cmd = ""

        if len(nmcli_con_details_cmd) > 0:
            nmcli_con_show_result = self.call_ext_prog(
                "nmcli --terse --fields NAME con")
            if nmcli_con_show_result['status'] == 0:
                for con in nmcli_con_show_result['output'].splitlines():
                    self.add_cmd_output("%s '%s'" %
                                        (nmcli_con_details_cmd, con))

            nmcli_dev_status_result = self.call_ext_prog(
                "nmcli --terse --fields DEVICE dev")
            if nmcli_dev_status_result['status'] == 0:
                for dev in nmcli_dev_status_result['output'].splitlines():
                    self.add_cmd_output("%s '%s'" %
                                        (nmcli_dev_details_cmd, dev))

    def postproc(self):
        for root, dirs, files in os.walk(
                "/etc/NetworkManager/system-connections"):
            for net_conf in files:
                self.do_file_sub(
                    "/etc/NetworkManager/system-connections/"+net_conf,
                    r"psk=(.*)", r"psk=***")
