# Copyright (C) 2013 Red Hat, Inc., Brent Eagles <beagles@redhat.com>
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


class OpenStackNeutron(Plugin):
    """OpenStack Networking
    """
    plugin_name = "openstack_neutron"
    profiles = ('openstack', 'openstack_controller', 'openstack_compute')

    def setup(self):

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/neutron/", sizelimit=self.limit)
        else:
            self.add_copy_spec("/var/log/neutron/*.log", sizelimit=self.limit)

        self.add_copy_spec("/etc/neutron/")
        self.add_copy_spec("/var/lib/neutron/")
        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

        vars = [p in os.environ for p in [
                'OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_NAME']]
        if not all(vars):
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

    def postproc(self):
        protect_keys = [
            "rabbit_password", "qpid_password", "nova_admin_password",
            "xenapi_connection_password", "password", "connection",
            "admin_password", "metadata_proxy_shared_secret", "eapi_password",
            "crd_password", "primary_l3_host_password", "serverauth",
            "ucsm_password", "ha_vrrp_auth_password", "ssl_key_password",
            "nsx_password", "vcenter_password", "edge_appliance_password",
            "tenant_admin_password", "apic_password", "server_auth"
        ]
        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)

        self.do_path_regex_sub("/etc/neutron/*", regexp, r"\1*********")


class DebianNeutron(OpenStackNeutron, DebianPlugin, UbuntuPlugin):
    packages = [
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
    ]

    def check_enabled(self):
        return self.is_installed("neutron-common")

    def setup(self):
        super(DebianNeutron, self).setup()
        self.add_copy_spec("/etc/sudoers.d/neutron_sudoers")


class RedHatNeutron(OpenStackNeutron, RedHatPlugin):

    packages = [
        'openstack-neutron',
        'openstack-neutron-linuxbridge'
        'openstack-neutron-metaplugin',
        'openstack-neutron-openvswitch',
        'openstack-neutron-bigswitch',
        'openstack-neutron-brocade',
        'openstack-neutron-cisco',
        'openstack-neutron-hyperv',
        'openstack-neutron-midonet',
        'openstack-neutron-nec'
        'openstack-neutron-nicira',
        'openstack-neutron-plumgrid',
        'openstack-neutron-ryu',
        'python-neutron',
        'python-neutronclient'
    ]

    def check_enabled(self):
        return self.is_installed("openstack-neutron")

    def setup(self):
        super(RedHatNeutron, self).setup()
        self.add_copy_spec("/etc/sudoers.d/neutron-rootwrap")

# vim: set et ts=4 sw=4 :
