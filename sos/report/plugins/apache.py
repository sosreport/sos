# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)


class Apache(Plugin):
    """The Apache plugin covers the upstream Apache webserver project,
    regardless of the packaged name; apache2 for Debian and Ubuntu, or httpd
    for Red Hat family distributions.

    The aim of this plugin is for Apache-specific information, not necessarily
    other projects that happen to place logs or similar files within the
    standardized apache directories. For example, OpenStack components that log
    to apache logging directories are excluded from this plugin and collected
    via their respective OpenStack plugins.

    Users can expect the collection of apachectl command output, apache server
    logs, and apache configuration files from this plugin.
    """

    short_desc = 'Apache http daemon'
    plugin_name = "apache"
    profiles = ('webserver', 'openshift')
    packages = ('httpd',)
    files = ('/var/www/',)

    option_list = [
        PluginOpt(name="log", default=False, desc="gathers all apache logs")
    ]

    def setup(self):
        # collect list of installed modules and verify config syntax.
        self.add_cmd_output([
            "apachectl -M",
            "apachectl -S",
            "apachectl -t"
        ], cmd_as_tag=True)

        # Other plugins collect these files;
        # do not collect them here to avoid collisions in the archive paths.
        subdirs = [
            'aodh',
            'ceilometer',
            'cinder',
            'foreman',
            'horizon',
            'keystone',
            'nova',
            'placement',
            'pulp'
        ]
        self.add_forbidden_path([
            "/var/log/%s*/%s*" % (self.apachepkg, sub) for sub in subdirs
        ])


class RedHatApache(Apache, RedHatPlugin):
    """
    On Red Hat distributions, the Apache plugin will also attempt to collect
    JBoss Web Server logs and configuration files.

    Note that for Red Hat distributions, this plugin explicitly collects for
    'httpd' installations. If you have installed apache from source or via any
    method that uses the name 'apache' instead of 'httpd', these collections
    will fail.
    """
    files = (
        '/etc/httpd/conf/httpd.conf',
        '/etc/httpd22/conf/httpd.conf',
        '/etc/httpd24/conf/httpd.conf'
    )
    apachepkg = 'httpd'

    def setup(self):

        self.add_file_tags({
            ".*/access_log": 'httpd_access_log',
            ".*/error_log": 'httpd_error_log',
            ".*/ssl_access_log": 'httpd_ssl_access_log',
            ".*/ssl_error_log": 'httpd_ssl_error_log'
        })

        super(RedHatApache, self).setup()

        # httpd versions, including those used for JBoss Web Server
        vers = ['', '22', '24']

        # Extrapolate all top-level config directories for each version, and
        # relevant config files within each
        etcdirs = ["/etc/httpd%s" % ver for ver in vers]
        confs = [
            "conf/httpd.conf",
            "conf.d/*.conf",
            "conf.modules.d/*.conf"
        ]

        # Extrapolate top-level logging directories for each version, and the
        # relevant log files within each
        logdirs = ["/var/log/httpd%s" % ver for ver in vers]
        logs = [
            "access_log",
            "error_log",
            "ssl_access_log",
            "ssl_error_log"
        ]

        self.add_forbidden_path([
            "%s/conf/password.conf" % etc for etc in etcdirs
        ])

        for edir in etcdirs:
            for conf in confs:
                self.add_copy_spec("%s/%s" % (edir, conf), tags="httpd_conf")

        if self.get_option("log") or self.get_option("all_logs"):
            self.add_copy_spec(logdirs)
        else:
            for ldir in logdirs:
                for log in logs:
                    self.add_copy_spec("%s/%s" % (ldir, log))

        self.add_service_status('httpd', tags='systemctl_httpd')


class DebianApache(Apache, DebianPlugin, UbuntuPlugin):
    files = ('/etc/apache2/apache2.conf',)
    apachepkg = 'apache'

    def setup(self):
        super(DebianApache, self).setup()
        self.add_copy_spec([
            "/etc/apache2/*",
            "/etc/default/apache2"
        ])

        self.add_service_status('apache2')

        # collect only the current log set by default
        self.add_copy_spec([
            "/var/log/apache2/access_log",
            "/var/log/apache2/error_log",
        ])
        if self.get_option("log") or self.get_option("all_logs"):
            self.add_copy_spec("/var/log/apache2/*")

# vim: set et ts=4 sw=4 :
