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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Services(Plugin):
    """System services
    """

    plugin_name = "services"
    profiles = ('system', 'boot')

    option_list = [("servicestatus", "get a status of all running services",
                    "slow", False)]

    def setup(self):
        self.add_copy_spec([
            "/etc/inittab",
            "/etc/rc.d"
        ])
        if self.get_option('servicestatus'):
            self.add_cmd_output("/sbin/service --status-all")
        self.add_cmd_output([
            "/sbin/runlevel",
            "ls /var/lock/subsys"
        ])


class RedHatServices(Services, RedHatPlugin):

    def setup(self):
        super(RedHatServices, self).setup()
        self.add_cmd_output("/sbin/chkconfig --list", root_symlink="chkconfig")


class DebianServices(Services, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianServices, self).setup()
        self.add_copy_spec("/etc/rc*.d")

        self.add_cmd_output("/sbin/initctl show-config",
                            root_symlink="initctl")
        if self.get_option('servicestatus'):
            self.add_cmd_output("/sbin/initctl list")

# vim: set et ts=4 sw=4 :
