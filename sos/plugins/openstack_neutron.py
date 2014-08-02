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


class Neutron(Plugin):
    """OpenStack Networking (quantum/neutron) related information
    """
    plugin_name = "neutron"

    option_list = [("log", "Gathers all Neutron logs", "slow", False),
                   ("quantum", "Overrides checks for newer Neutron components",
                    "fast", False)]

    component_name = "neutron"

    def setup(self):
        if os.path.exists("/etc/neutron/") and \
                self.get_option("quantum", False):
            self.component_name = self.plugin_name
        else:
            self.component_name = "quantum"

        self.add_copy_specs([
            "/etc/%s/" % self.component_name,
            "/var/log/%s/" % self.component_name
        ])

        self.netns_dumps()
        self.get_ovs_dumps()

    def get_ovs_dumps(self):
        # Check to see if we are using the Open vSwitch plugin. If not we
        # should be able to skip the rest of the dump.
        ovs_conf_check = self.call_ext_prog(
            'grep "^core_plugin.*openvswitch" ' +
            ("/etc/%s/*.conf" + self.component_name))
        if not (ovs_conf_check['status'] == 0):
            return
        if len(ovs_conf_check['output'].splitlines()) == 0:
            return

        # The '-s' option enables dumping of packet counters on the
        # ports.
        self.add_cmd_output("ovs-dpctl -s show")

        # The '-t 5' adds an upper bound on how long to wait to connect
        # to the Open vSwitch server, avoiding hangs when running sosreport.
        self.add_cmd_output("ovs-vsctl -t 5 show")

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
            self.add_copy_specs(lease_directories)

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
        self.add_cmd_outputs([
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
                self.add_cmd_outputs([
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


class DebianNeutron(Neutron, DebianPlugin, UbuntuPlugin):
    """OpenStack Neutron related information for Debian based distributions
    """
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


class RedHatNeutron(Neutron, RedHatPlugin):
    """OpenStack Neutron related information for Red Hat distributions
    """

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

# vim: et ts=4 sw=4
