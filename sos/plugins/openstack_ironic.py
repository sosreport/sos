# Copyright (C) 2015 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class OpenStackIronic(Plugin):
    """OpenStack Ironic
    """
    plugin_name = "openstack_ironic"
    profiles = ('openstack', 'openstack_undercloud')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/ironic"

    def setup(self):
        self.conf_list = [
            "/etc/ironic/*",
            self.var_puppet_gen + "/etc/ironic/*",
            self.var_puppet_gen + "_api/etc/ironic/*"
        ]
        self.add_copy_spec([
            "/etc/ironic/",
            self.var_puppet_gen + "/etc/xinetd.conf",
            self.var_puppet_gen + "/etc/xinetd.d/",
            self.var_puppet_gen + "/etc/ironic/",
            self.var_puppet_gen + "/etc/httpd/conf/",
            self.var_puppet_gen + "/etc/httpd/conf.d/",
            self.var_puppet_gen + "/etc/httpd/conf.modules.d/*.conf",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf",
            self.var_puppet_gen + "_api/etc/ironic/",
            self.var_puppet_gen + "_api/etc/httpd/conf/",
            self.var_puppet_gen + "_api/etc/httpd/conf.d/",
            self.var_puppet_gen + "_api/etc/httpd/conf.modules.d/*.conf",
            self.var_puppet_gen + "_api/etc/my.cnf.d/tripleo.cnf"
        ])

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/ironic/",
                "/var/log/containers/ironic/",
                "/var/log/containers/httpd/ironic-api/"
            ], sizelimit=self.limit)
        else:
            self.add_copy_spec([
                "/var/log/ironic/*.log",
                "/var/log/containers/ironic/*.log",
                "/var/log/containers/httpd/ironic-api/*log"
            ], sizelimit=self.limit)

        self.add_cmd_output('ls -laRt /var/lib/ironic/')
        self.add_cmd_output(
            'ls -laRt ' + self.var_puppet_gen + '/var/lib/ironic/'
        )

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

        vars_all = [p in os.environ for p in [
                    'OS_USERNAME', 'OS_PASSWORD']]

        vars_any = [p in os.environ for p in [
                    'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

        if not (all(vars_all) and any(vars_any)):
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            self.add_cmd_output("openstack baremetal node list --long")
            self.add_cmd_output("openstack baremetal port list")

    def apply_regex_sub(self, regexp, subst):
        for conf in self.conf_list:
            self.do_path_regex_sub(conf, regexp, subst)

    def postproc(self):
        protect_keys = [
            "dns_passkey", "memcache_secret_key", "rabbit_password",
            "password", "qpid_password", "admin_password", "ssl_key_password",
            "os_password"
        ]
        connection_keys = ["connection", "sql_connection"]

        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1*********"
        )
        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*(.*)://(\w*):)(.*)(@(.*))" %
            "|".join(connection_keys),
            r"\1*********\6"
        )


class DebianIronic(OpenStackIronic, DebianPlugin, UbuntuPlugin):

    packages = [
        'ironic-api',
        'ironic-common',
        'ironic-conductor',
    ]

    def setup(self):
        super(DebianIronic, self).setup()


class RedHatIronic(OpenStackIronic, RedHatPlugin):

    packages = [
        'openstack-ironic-api',
        'openstack-ironic-common',
        'openstack-ironic-conductor',
    ]

    discoverd_packages = [
        'openstack-ironic-discoverd',
        'openstack-ironic-discoverd-ramdisk'
    ]

    def setup(self):
        super(RedHatIronic, self).setup()

        # is the optional ironic-discoverd service installed?
        if any([self.is_installed(p) for p in self.discoverd_packages]):
            self.conf_list.append('/etc/ironic-discoverd/*')
            self.add_copy_spec('/etc/ironic-discoverd/')
            self.add_copy_spec('/var/lib/ironic-discoverd/')
            self.add_copy_spec('/var/log/ironic-discoverd/')

            self.add_journal(units="openstack-ironic-discoverd")
            self.add_journal(units="openstack-ironic-discoverd-dnsmasq")

# vim: set et ts=4 sw=4 :
