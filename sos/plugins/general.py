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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin


class General(Plugin):
    """general system information"""

    plugin_name = "general"
    profiles = ('system', 'sysmgmt')

    def setup(self):
        self.add_copy_spec([
            "/etc/sos.conf",
            "/etc/sysconfig",
            "/proc/stat",
            "/var/log/pm/suspend.log",
            "/etc/hostid",
            "/etc/localtime",
            "/etc/os-release"
        ])

        self.add_cmd_output("hostname -f")
        self.add_cmd_output("hostname", root_symlink='hostname')

        self.add_cmd_output("date", root_symlink="date")
        self.add_cmd_output("uptime", root_symlink="uptime")


class RedHatGeneral(General, RedHatPlugin):

    def setup(self):
        super(RedHatGeneral, self).setup()

        self.add_copy_spec([
            "/etc/redhat-release",
            "/etc/fedora-release",
            "/var/log/up2date"
        ])

    def postproc(self):
        self.do_file_sub("/etc/sysconfig/rhn/up2date",
                         r"(\s*proxyPassword\s*=\s*)\S+", r"\1***")


class DebianGeneral(General, DebianPlugin):

    def setup(self):
        super(DebianGeneral, self).setup()
        self.add_copy_spec([
            "/etc/default",
            "/etc/lsb-release",
            "/etc/debian_version"
        ])

# vim: set et ts=4 sw=4 :
