# Copyright (C) 2013 Red Hat, Inc., Brent Eagles <beagles@redhat.com>
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


class OpenStackNeutron(Plugin):

    short_desc = 'OpenStack Networking'
    plugin_name = "openstack_neutron"
    profiles = ('openstack', 'openstack_controller', 'openstack_compute')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/neutron"

    def setup(self):
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/neutron/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/neutron/*.log",
            ])

        self.add_copy_spec([
            "/etc/neutron/",
            self.var_puppet_gen + "/etc/neutron/",
            self.var_puppet_gen + "/etc/default/neutron-server",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf"
        ])
        # copy whole /var/lib/neutron except for potentially huge lock subdir;
        # rather take a list of files in the dir only
        self.add_copy_spec("/var/lib/neutron/")
        self.add_forbidden_path("/var/lib/neutron/lock")
        self.add_cmd_output("ls -laZR /var/lib/neutron/lock")

        vars_all = [p in os.environ for p in [
                    'OS_USERNAME', 'OS_PASSWORD']]

        vars_any = [p in os.environ for p in [
                    'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

        if not (all(vars_all) and any(vars_any)):
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            self.add_cmd_output("openstack subnet list")
            self.add_cmd_output("openstack port list")
            self.add_cmd_output("openstack router list")
            self.add_cmd_output("openstack network agent list")
            self.add_cmd_output("openstack network list")
            self.add_cmd_output("openstack extension list")
            self.add_cmd_output("openstack floating ip list")
            self.add_cmd_output("openstack security group list")

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/neutron/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/neutron/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "rabbit_password", "qpid_password", "nova_admin_password",
            "xenapi_connection_password", "password", "server_auth",
            "admin_password", "metadata_proxy_shared_secret", "eapi_password",
            "crd_password", "primary_l3_host_password", "serverauth",
            "ucsm_password", "ha_vrrp_auth_password", "ssl_key_password",
            "nsx_password", "vcenter_password", "edge_appliance_password",
            "tenant_admin_password", "apic_password", "transport_url"
        ]
        connection_keys = ["connection"]

        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1*********"
        )
        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*(.*)://(\w*):)(.*)(@(.*))" %
            "|".join(connection_keys),
            r"\1*********\6"
        )


class DebianNeutron(OpenStackNeutron, DebianPlugin, UbuntuPlugin):
    packages = (
        'neutron-common',
        'neutron-plugin-cisco',
        'neutron-plugin-linuxbridge-agent',
        'neutron-plugin-nicira',
        'neutron-plugin-openvswitch',
        'neutron-plugin-openvswitch-agent',
        'neutron-plugin-ryu',
        'neutron-plugin-ryu-agent',
        'neutron-server',
        'python-neutron',
        'python-neutronclient'
    )

    def check_enabled(self):
        return self.is_installed("neutron-common")

    def setup(self):
        super(DebianNeutron, self).setup()
        self.add_copy_spec("/etc/sudoers.d/neutron_sudoers")


class RedHatNeutron(OpenStackNeutron, RedHatPlugin):

    packages = ('openstack-selinux',)

    def setup(self):
        super(RedHatNeutron, self).setup()
        self.add_copy_spec("/etc/sudoers.d/neutron-rootwrap")

# vim: set et ts=4 sw=4 :
