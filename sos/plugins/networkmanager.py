# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin
import os


class NetworkManager(Plugin, RedHatPlugin, UbuntuPlugin):
    """NetworkManager service configuration
    """

    plugin_name = 'networkmanager'
    profiles = ('network', 'hardware', 'system')
    packages = ('NetworkManager', 'network-manager')

    def setup(self):
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
                    if con[0:7] == 'Warning':
                        continue
                    # nm names may contain embedded quotes (" and '). These
                    # will cause an exception in shlex.split() if the quotes
                    # are unbalanced. This may happen with names like:
                    # "Foobar's Wireless Network". Although the problen will
                    # occur for both single and double quote characters the
                    # former is considerably more likely in object names since
                    # it is syntactically valid in many human languages.
                    #
                    # Reverse the normal sos quoting convention here and place
                    # double quotes around the innermost quoted string.
                    self.add_cmd_output('%s "%s"' %
                                        (nmcli_con_details_cmd, con))

            nmcli_dev_status_result = self.call_ext_prog(
                "nmcli --terse --fields DEVICE dev")
            if nmcli_dev_status_result['status'] == 0:
                for dev in nmcli_dev_status_result['output'].splitlines():
                    if dev[0:7] == 'Warning':
                        continue
                    # See above comment describing quoting conventions.
                    self.add_cmd_output('%s "%s"' %
                                        (nmcli_dev_details_cmd, dev))

    def postproc(self):
        for root, dirs, files in os.walk(
                "/etc/NetworkManager/system-connections"):
            for net_conf in files:
                self.do_file_sub(
                    "/etc/NetworkManager/system-connections/"+net_conf,
                    r"psk=(.*)", r"psk=***")


# vim: set et ts=4 sw=4 :
