# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Apache(Plugin):
    """Apache http daemon
    """
    plugin_name = "apache"
    profiles = ('webserver', 'openshift')
    packages = ('httpd',)
    files = ('/var/www/',)

    option_list = [
        ("log", "gathers all apache logs", "slow", False)
    ]

    def setup(self):
        # collect list of installed modules
        self.add_cmd_output(["apachectl -M"])


class RedHatApache(Apache, RedHatPlugin):
    files = (
        '/etc/httpd/conf/httpd.conf',
        '/etc/httpd22/conf/httpd.conf',
        '/etc/httpd24/conf/httpd.conf'
    )

    def setup(self):
        super(RedHatApache, self).setup()

        self.add_copy_spec([
            "/etc/httpd/conf/httpd.conf",
            "/etc/httpd/conf.d/*.conf",
            "/etc/httpd/conf.modules.d/*.conf",
            # JBoss Enterprise Web Server 2.x
            "/etc/httpd22/conf/httpd.conf",
            "/etc/httpd22/conf.d/*.conf",
            # Red Hat JBoss Web Server 3.x
            "/etc/httpd24/conf/httpd.conf",
            "/etc/httpd24/conf.d/*.conf",
            "/etc/httpd24/conf.modules.d/*.conf",
        ])

        self.add_forbidden_path("/etc/httpd/conf/password.conf")

        # determine how much logs to collect
        self.limit = None if self.get_option("all_logs") else 5

        # collect only the current log set by default
        self.add_copy_spec("/var/log/httpd/access_log", self.limit)
        self.add_copy_spec("/var/log/httpd/error_log", self.limit)
        self.add_copy_spec("/var/log/httpd/ssl_access_log", self.limit)
        self.add_copy_spec("/var/log/httpd/ssl_error_log", self.limit)
        # JBoss Enterprise Web Server 2.x
        self.add_copy_spec("/var/log/httpd22/access_log", self.limit)
        self.add_copy_spec("/var/log/httpd22/error_log", self.limit)
        self.add_copy_spec("/var/log/httpd22/ssl_access_log", self.limit)
        self.add_copy_spec("/var/log/httpd22/ssl_error_log", self.limit)
        # Red Hat JBoss Web Server 3.x
        self.add_copy_spec("/var/log/httpd24/access_log", self.limit)
        self.add_copy_spec("/var/log/httpd24/error_log", self.limit)
        self.add_copy_spec("/var/log/httpd24/ssl_access_log", self.limit)
        self.add_copy_spec("/var/log/httpd24/ssl_error_log", self.limit)
        if self.get_option("log") or self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/httpd/*",
                # JBoss Enterprise Web Server 2.x
                "/var/log/httpd22/*",
                # Red Hat JBoss Web Server 3.x
                "/var/log/httpd24/*"
            ])


class DebianApache(Apache, DebianPlugin, UbuntuPlugin):
    files = ('/etc/apache2/apache2.conf',)

    def setup(self):
        super(DebianApache, self).setup()
        self.add_copy_spec([
            "/etc/apache2/*",
            "/etc/default/apache2"
        ])

        # determine how much logs to collect
        self.limit = None if self.get_option("all_logs") else 15

        # collect only the current log set by default
        self.add_copy_spec("/var/log/apache2/access_log", self.limit)
        self.add_copy_spec("/var/log/apache2/error_log", self.limit)
        if self.get_option("log") or self.get_option("all_logs"):
            self.add_copy_spec("/var/log/apache2/*")

# vim: set et ts=4 sw=4 :
