# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, UbuntuPlugin


class Landscape(Plugin, UbuntuPlugin):
    """Ubuntu Landscape client
    """

    plugin_name = 'landscape'
    profiles = ('sysmgmt',)
    files = ('/etc/landscape/client.conf', '/etc/landscape/service.conf')
    packages = ('landscape-client', 'landscape-server')

    def setup(self):
        self.add_copy_spec("/etc/landscape/client.conf")
        self.add_copy_spec("/etc/default/landscape-client")
        self.add_copy_spec("/etc/landscape/service.conf")
        self.add_copy_spec("/etc/landscape/service.conf.old")
        self.add_copy_spec("/etc/default/landscape-server")
        if not self.get_option("all_logs"):
            self.add_copy_spec("/var/log/landscape/*.log")
            self.add_copy_spec("/var/log/landscape-server/*.log")
        else:
            self.add_copy_spec("/var/log/landscape")
            self.add_copy_spec("/var/log/landscape-server")
        self.add_cmd_output("gpg --verify /etc/landscape/license.txt")
        self.add_cmd_output("head -n 5 /etc/landscape/license.txt")
        self.add_cmd_output("lsctl status")

    def postproc(self):
        self.do_file_sub(
            "/etc/landscape/client.conf",
            r"registration_password(.*)",
            r"registration_password[********]"
        )
        self.do_file_sub(
            "/etc/landscape/service.conf",
            r"password = (.*)",
            r"password = [********]"
        )
        self.do_file_sub(
            "/etc/landscape/service.conf",
            r"store_password = (.*)",
            r"store_password = [********]"
        )
        self.do_file_sub(
            "/etc/landscape/service.conf",
            r"secret-token = (.*)",
            r"secret-token = [********]"
        )
        self.do_file_sub(
            "/etc/landscape/service.conf.old",
            r"password = (.*)",
            r"password = [********]"
        )
        self.do_file_sub(
            "/etc/landscape/service.conf.old",
            r"store_password = (.*)",
            r"store_password = [********]"
        )
        self.do_file_sub(
            "/etc/landscape/service.conf.old",
            r"secret-token = (.*)",
            r"secret-token = [********]"
        )

# vim: set et ts=4 sw=4 :
