# Copyright (C) 2015 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/ironic/",
                "/var/log/containers/ironic/",
                "/var/log/containers/httpd/ironic-api/"
            ])
        else:
            self.add_copy_spec([
                "/var/log/ironic/*.log",
                "/var/log/containers/ironic/*.log",
                "/var/log/containers/httpd/ironic-api/*log"
            ])

        for path in ['/var/lib/ironic', '/httpboot', '/tftpboot']:
            self.add_cmd_output('ls -laRt %s' % path)
            self.add_cmd_output('ls -laRt %s' % (self.var_puppet_gen + path))

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

        vars_all = [p in os.environ for p in [
                    'OS_USERNAME', 'OS_PASSWORD']]

        vars_any = [p in os.environ for p in [
                    'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

        self.osc_available = all(vars_all) and any(vars_any)

        if not self.osc_available:
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            self.add_cmd_output("openstack baremetal driver list --long")
            self.add_cmd_output("openstack baremetal node list --long")
            self.add_cmd_output("openstack baremetal port list --long")
            self.add_cmd_output("openstack baremetal port group list --long")

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

    def collect_introspection_data(self):
        uuids_result = self.call_ext_prog('openstack baremetal node list '
                                          '-f value -c UUID')
        if uuids_result['status']:
            self.soslog.warning('Failed to fetch list of ironic node UUIDs, '
                                'introspection data won\'t be collected')
            return

        uuids = [uuid for uuid in uuids_result['output'].split()
                 if uuid.strip()]
        for uuid in uuids:
            self.add_cmd_output('openstack baremetal introspection '
                                'data save %s' % uuid)

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

        # ironic-discoverd was renamed to ironic-inspector in Liberty
        self.conf_list.append('/etc/ironic-inspector/*')
        self.conf_list.append(self.var_puppet_gen + '/etc/ironic-inspector/*')
        self.add_copy_spec('/etc/ironic-inspector/')
        self.add_copy_spec(self.var_puppet_gen + '/etc/ironic-inspector/')
        self.add_copy_spec('/var/lib/ironic-inspector/')
        if self.get_option("all_logs"):
            self.add_copy_spec('/var/log/ironic-inspector/')
            self.add_copy_spec('/var/log/containers/ironic-inspector/')
        else:
            self.add_copy_spec('/var/log/ironic-inspector/*.log')
            self.add_copy_spec('/var/log/ironic-inspector/ramdisk/')
            self.add_copy_spec('/var/log/containers/ironic-inspector/*.log')
            self.add_copy_spec('/var/log/containers/ironic-inspector/ramdisk/')

        self.add_journal(units="openstack-ironic-inspector-dnsmasq")

        if self.osc_available:
            self.add_cmd_output("openstack baremetal introspection list")
            if self.get_option("all_logs"):
                self.collect_introspection_data()

# vim: set et ts=4 sw=4 :
