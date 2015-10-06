# Copyright (C) 2013 Red Hat, Inc., Brent Eagles <beagles@redhat.com>

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

import os
import re

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

# The Networking plugin includes most of what is needed from a snapshot
# of the networking, so we only need to focus on the parts that are specific
# to OpenStack Networking. The Process plugin should capture the dnsmasq
# command line. The libvirt plugin grabs the instance's XML definition which
# has the interface names for an instance. So what remains is relevant database
# info...


class OpenStackNeutron(Plugin):
    """OpenStack Networking
    """
    plugin_name = "openstack_neutron"
    profiles = ('openstack', 'openstack_controller', 'openstack_compute')

    option_list = [("quantum", "Overrides checks for newer Neutron components",
                    "fast", False)]

    component_name = "neutron"

    def setup(self):
        if not os.path.exists("/etc/neutron/") or self.get_option("quantum"):
            self.component_name = "quantum"

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec_limit("/var/log/%s/" % self.component_name,
                                     sizelimit=self.limit)
        else:
            self.add_copy_spec_limit("/var/log/%s/*.log" % self.component_name,
                                     sizelimit=self.limit)

        self.add_copy_spec("/etc/%s/" % self.component_name)

        self.netns_dumps()

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

        self.do_path_regex_sub("/etc/%s/*" % self.component_name,
                               regexp, r"\1*********")

    def netns_dumps(self):
        # It would've been beautiful if we could get parts of the networking
        # plugin to run in different namespaces. There are a couple of options
        # in the short term: create a local instance and "borrow" some of the
        # functionality, or simply copy some of the functionality.
        prefixes = ["qdhcp", "qrouter"]
        ip_netns_result = self.call_ext_prog("ip netns")
        if not (ip_netns_result['status'] == 0):
            return
        nslist = ip_netns_result['output']
        lease_directories = []
        if nslist:
            for nsname in nslist.splitlines():
                prefix, netid = nsname.split('-', 1)
                if len(netid) > 0 and prefix in prefixes:
                    self.ns_gather_data(nsname)
                    lease_directories.append(
                        "/var/lib/%s/dhcp/%s/" %
                        (self.component_name, netid))
            self.add_copy_spec(lease_directories)

    # TODO: Refactor! Copied from Networking plugin.
    def get_interface_name(self, ip_addr_out):
        """Return a dictionary for which key are interface name according to
        the output of ifconifg-a stored in ifconfig_file.
        """
        out = {}
        for line in ip_addr_out.splitlines():
            match = re.match('.*link/ether', line)
            if match:
                int = match.string.split(':')[1].lstrip()
                out[int] = True
        return out

    def ns_gather_data(self, nsname):
        cmd_prefix = "ip netns exec %s " % nsname
        self.add_cmd_output([
            cmd_prefix + "iptables-save",
            cmd_prefix + "ifconfig -a",
            cmd_prefix + "route -n"
        ])
        # borrowed from networking plugin
        ip_addr_result = self.call_ext_prog(cmd_prefix + "ip -o addr")
        if ip_addr_result['status'] == 0:
            for eth in self.get_interface_name(ip_addr_result['output']):
                # Most, if not all, IFs in the namespaces are going to be
                # virtual. The '-a', '-c' and '-g' options are not likely to be
                # supported so these ops are not copied from the network
                # plugin.
                self.add_cmd_output([
                    cmd_prefix + "ethtool "+eth,
                    cmd_prefix + "ethtool -i "+eth,
                    cmd_prefix + "ethtool -k "+eth,
                    cmd_prefix + "ethtool -S "+eth
                ])

        # As all of the bridges are in the "global namespace", we do not need
        # to gather info on them.

    def gen_pkg_tuple(self, packages):
        names = []
        for p in packages:
            names.append(p % {"comp": self.component_name})
        return tuple(names)


class DebianNeutron(OpenStackNeutron, DebianPlugin, UbuntuPlugin):
    package_list_template = [
        '%(comp)s-common',
        '%(comp)s-plugin-cisco',
        '%(comp)s-plugin-linuxbridge-agent',
        '%(comp)s-plugin-nicira',
        '%(comp)s-plugin-openvswitch',
        '%(comp)s-plugin-openvswitch-agent',
        '%(comp)s-plugin-ryu',
        '%(comp)s-plugin-ryu-agent',
        '%(comp)s-server',
        'python-%(comp)s',
        'python-%(comp)sclient'
    ]

    def check_enabled(self):
        return self.is_installed("%s-common" % self.component_name)

    def setup(self):
        super(DebianNeutron, self).setup()
        self.packages = self.gen_pkg_tuple(self.package_list_template)
        self.add_copy_spec("/etc/sudoers.d/%s_sudoers" % self.component_name)


class RedHatNeutron(OpenStackNeutron, RedHatPlugin):

    package_list_template = [
        'openstack-%(comp)s',
        'openstack-%(comp)s-linuxbridge'
        'openstack-%(comp)s-metaplugin',
        'openstack-%(comp)s-openvswitch',
        'openstack-%(comp)s-bigswitch',
        'openstack-%(comp)s-brocade',
        'openstack-%(comp)s-cisco',
        'openstack-%(comp)s-hyperv',
        'openstack-%(comp)s-midonet',
        'openstack-%(comp)s-nec'
        'openstack-%(comp)s-nicira',
        'openstack-%(comp)s-plumgrid',
        'openstack-%(comp)s-ryu',
        'python-%(comp)s',
        'python-%(comp)sclient'
    ]

    def check_enabled(self):
        return self.is_installed("openstack-%s" % self.component_name)

    def setup(self):
        super(RedHatNeutron, self).setup()
        self.packages = self.gen_pkg_tuple(self.package_list_template)
        self.add_copy_spec("/etc/sudoers.d/%s-rootwrap" % self.component_name)

# vim: set et ts=4 sw=4 :
