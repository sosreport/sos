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


class Auditd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Audit daemon information
    """

    plugin_name = 'auditd'
    profiles = ('system', 'security')

    packages = ('audit',)

    def setup(self):
        self.add_copy_spec([
            "/etc/audit/auditd.conf",
            "/etc/audit/audit.rules"
        ])
        self.add_cmd_output("ausearch --input-logs -m avc,user_avc -ts today")

        if not self.get_option("all_logs"):
            limit = self.get_option("log_size")
            self.add_copy_spec_limit("/var/log/audit/audit.log",
                                     sizelimit=limit)
        else:
            self.add_copy_spec("/var/log/audit")

# vim: set et ts=4 sw=4 :
