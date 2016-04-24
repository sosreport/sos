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

from sos.plugins import Plugin, RedHatPlugin


class Satellite(Plugin, RedHatPlugin):
    """RHN Satellite and Spacewalk
    """

    plugin_name = 'satellite'
    profiles = ('sysmgmt',)
    satellite = False
    proxy = False

    option_list = [("log", 'gathers all apache logs', 'slow', False)]

    def rhn_package_check(self):
        self.satellite = self.is_installed("rhns-satellite-tools") \
            or self.is_installed("spacewalk-java") \
            or self.is_installed("rhn-base")
        self.proxy = self.is_installed("rhns-proxy-tools") \
            or self.is_installed("spacewalk-proxy-management") \
            or self.is_installed("rhn-proxy-management")
        return self.satellite or self.proxy

    def check_enabled(self):
        # enable if any related package is installed
        return self.rhn_package_check()

    def setup(self):
        self.rhn_package_check()
        self.add_copy_spec([
            "/etc/httpd/conf*",
            "/etc/rhn",
            "/var/log/rhn*"
        ])

        if self.get_option("log"):
            self.add_copy_spec("/var/log/httpd")

        # all these used to go in $DIR/mon-logs/
        self.add_copy_spec([
            "/opt/notification/var/*.log*",
            "/var/tmp/ack_handler.log*",
            "/var/tmp/enqueue.log*"
        ])

        # monitoring scout logs
        self.add_copy_spec([
            "/home/nocpulse/var/*.log*",
            "/home/nocpulse/var/commands/*.log*",
            "/var/tmp/ack_handler.log*",
            "/var/tmp/enqueue.log*",
            "/var/log/nocpulse/*.log*",
            "/var/log/notification/*.log*",
            "/var/log/nocpulse/TSDBLocalQueue/TSDBLocalQueue.log"
        ])

        self.add_copy_spec("/root/ssl-build")
        self.add_cmd_output("rhn-schema-version",
                            root_symlink="database-schema-version")
        self.add_cmd_output("rhn-charsets",
                            root_symlink="database-character-sets")

        if self.satellite:
            self.add_copy_spec([
                "/etc/tnsnames.ora",
                "/etc/jabberd"
            ])
            self.add_cmd_output(
                "spacewalk-debug --dir %s"
                % self.get_cmd_output_path(name="spacewalk-debug"))

        if self.proxy:
            self.add_copy_spec(["/etc/squid", "/var/log/squid"])

# vim: set et ts=4 sw=4 :
