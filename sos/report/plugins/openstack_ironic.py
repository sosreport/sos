# Copyright (C) 2015 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class OpenStackIronic(Plugin):

    short_desc = 'OpenStack Ironic'
    plugin_name = "openstack_ironic"
    profiles = ('openstack', 'openstack_undercloud')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/ironic"
    ins_puppet_gen = var_puppet_gen + "_inspector"

    def setup(self):

        in_container = self.container_exists('.*ironic_api')

        if in_container:
            self.conf_list = [
                self.var_puppet_gen + "/etc/ironic/*",
                self.var_puppet_gen + "/etc/ironic-inspector/*",
                self.var_puppet_gen + "_api/etc/ironic/*",
                self.ins_puppet_gen + "/etc/ironic-inspector/*",
                self.ins_puppet_gen + "/var/lib/httpboot/inspector.ipxe"
            ]
            self.add_copy_spec([
                "/var/lib/ironic-inspector/",
                "/var/log/containers/ironic-inspector/ramdisk/",
                self.var_puppet_gen + "/etc/xinetd.conf",
                self.var_puppet_gen + "/etc/xinetd.d/",
                self.var_puppet_gen + "/etc/ironic/",
                self.var_puppet_gen + "/etc/ironic-inspector/",
                self.var_puppet_gen + "/etc/httpd/conf/",
                self.var_puppet_gen + "/etc/httpd/conf.d/",
                self.var_puppet_gen + "/etc/httpd/conf.modules.d/*.conf",
                self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf",
                self.var_puppet_gen + "_api/etc/ironic/",
                self.var_puppet_gen + "_api/etc/httpd/conf/",
                self.var_puppet_gen + "_api/etc/httpd/conf.d/",
                self.var_puppet_gen + "_api/etc/httpd/conf.modules.d/*.conf",
                self.var_puppet_gen + "_api/etc/my.cnf.d/tripleo.cnf",
                self.ins_puppet_gen + "/etc/ironic-inspector/*",
                self.ins_puppet_gen + "/var/lib/httpboot/inspector.ipxe"
            ])

            if self.get_option("all_logs"):
                self.add_copy_spec([
                    "/var/log/containers/ironic/",
                    "/var/log/containers/ironic-inspector/"
                ])
            else:
                self.add_copy_spec([
                    "/var/log/containers/ironic/*.log",
                    "/var/log/containers/ironic-inspector/*.log",
                ])

            for path in ['/var/lib/ironic', '/httpboot', '/tftpboot',
                         self.ins_puppet_gen + '/var/lib/httpboot/',
                         self.ins_puppet_gen + '/var/lib/tftpboot/']:
                self.add_cmd_output('ls -laRt %s' % path)
                self.add_cmd_output('ls -laRt %s' %
                                    (self.var_puppet_gen + path))

            # Let's get the packages from the containers, always helpful when
            # troubleshooting.
            for container_name in ['ironic_inspector_dnsmasq',
                                   'ironic_inspector', 'ironic_pxe_http',
                                   'ironic_pxe_tftp', 'ironic_neutron_agent',
                                   'ironic_conductor', 'ironic_api']:
                if self.container_exists('.*' + container_name):
                    self.add_cmd_output(self.fmt_container_cmd(container_name,
                                                               'rpm -qa'))

        else:
            self.conf_list = [
                "/etc/ironic/*",
                "/etc/ironic-inspector/*",
            ]
            self.add_copy_spec([
                "/etc/ironic/",
                "/etc/ironic-inspector/",
                "/var/lib/ironic-inspector/",
                "/var/log/ironic-inspector/ramdisk/",
                "/etc/my.cnf.d/tripleo.cnf",
                "/var/lib/httpboot/inspector.ipxe"
            ])

            if self.get_option("all_logs"):
                self.add_copy_spec([
                    "/var/log/ironic/",
                    "/var/log/ironic-inspector/",
                ])
            else:
                self.add_copy_spec([
                    "/var/log/ironic/*.log",
                    "/var/log/ironic-inspector/*.log",
                ])

            for path in ['/var/lib/ironic', '/httpboot', '/tftpboot']:
                self.add_cmd_output('ls -laRt %s' % path)

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
            "os_password", "transport_url"
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

    packages = ('ironic-api', 'ironic-common', 'ironic-conductor')

    def setup(self):
        super(DebianIronic, self).setup()


class RedHatIronic(OpenStackIronic, RedHatPlugin):

    packages = ('openstack-selinux',)

    discoverd_packages = [
        'openstack-ironic-discoverd',
        'openstack-ironic-discoverd-ramdisk'
    ]

    def collect_introspection_data(self):
        uuids_result = self.collect_cmd_output(
            'openstack baremetal node list -f value -c UUID'
        )
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

        # ironic-discoverd was renamed to ironic-inspector in Liberty
        # is the optional ironic-discoverd service installed?
        if any([self.is_installed(p) for p in self.discoverd_packages]):
            self.conf_list.append('/etc/ironic-discoverd/*')
            self.add_copy_spec('/etc/ironic-discoverd/')
            self.add_copy_spec('/var/lib/ironic-discoverd/')
            self.add_copy_spec('/var/log/ironic-discoverd/')

            self.add_journal(units="openstack-ironic-discoverd")
            self.add_journal(units="openstack-ironic-discoverd-dnsmasq")

        self.add_journal(units="openstack-ironic-inspector-dnsmasq")

        if self.osc_available:
            self.add_cmd_output("openstack baremetal introspection list")
            if self.get_option("all_logs"):
                self.collect_introspection_data()

# vim: set et ts=4 sw=4 :
