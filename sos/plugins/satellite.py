# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Satellite(Plugin, RedHatPlugin):
    """RHN Satellite and Spacewalk
    """

    plugin_name = 'satellite'
    profiles = ('sysmgmt',)
    verify_packages = ('spacewalk.*',)
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
                % self.get_cmd_output_path(name="spacewalk-debug"),
                timeout=900)

        if self.proxy:
            self.add_copy_spec(["/etc/squid", "/var/log/squid"])

# vim: set et ts=4 sw=4 :
