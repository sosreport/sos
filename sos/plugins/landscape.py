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
            limit = self.get_option("log_size")
            self.add_copy_spec_limit("/var/log/landscape/*.log",
                                     sizelimit=limit)
            self.add_copy_spec_limit("/var/log/landscape-server/*.log",
                                     sizelimit=limit)
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
