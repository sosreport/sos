## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class openstack(Plugin):
    """openstack related information
    """
    plugin_name = "openstack"

    optionList = [("log", "gathers all openstack logs", "slow", False)]


class DebianOpenStack(openstack, DebianPlugin, UbuntuPlugin):
    """OpenStack related information for Debian based distributions
    """

    packages = ('glance',
                'glance-api',
                'glance-client',
                'glance-common',
                'glance-registry',
                'keystone',
                'melange',
                'nova-api-ec2',
                'nova-api-metadata',
                'nova-api-os-compute',
                'nova-api-os-volume',
                'nova-common',
                'nova-compute',
                'nova-compute-kvm',
                'nova-compute-lxc',
                'nova-compute-qemu',
                'nova-compute-uml',
                'nova-compute-xcp',
                'nova-compute-xen',
                'nova-xcp-plugins',
                'nova-consoleauth',
                'nova-network',
                'nova-scheduler',
                'nova-volume',
                'novnc',
                'openstack-dashboard',
                'quantum-common',
                'quantum-plugin-cisco',
                'quantum-plugin-linuxbridge-agent',
                'quantum-plugin-nicira',
                'quantum-plugin-openvswitch',
                'quantum-plugin-openvswitch-agent',
                'quantum-plugin-ryu',
                'quantum-plugin-ryu-agent',
                'quantum-server',
                'swift',
                'swift-account',
                'swift-container',
                'swift-object',
                'swift-proxy',
                'swauth',
                'python-django-horizon',
                'python-glance',
                'python-keystone',
                'python-keystoneclient',
                'python-melange',
                'python-nova',
                'python-novaclient',
                'python-novnc',
                'python-quantum',
                'python-quantumclient',
                'python-swift',
                'python-swauth')

    def setup(self):
        # Nova
        if os.path.exists("/usr/bin/nova-manage"):
            self.collectExtOutput(
                "/usr/bin/nova-manage config list 2>/dev/null | sort",
                suggest_filename="nova_config_list")
            self.collectExtOutput(
                "/usr/bin/nova-manage service list 2>/dev/null",
                suggest_filename="nova_service_list")
            self.collectExtOutput(
                "/usr/bin/nova-manage db version 2>/dev/null",
                suggest_filename="nova_db_version")
            self.collectExtOutput(
                "/usr/bin/nova-manage fixed list 2>/dev/null",
                suggest_filename="nova_fixed_ip_list")
            self.collectExtOutput(
                "/usr/bin/nova-manage floating list 2>/dev/null",
                suggest_filename="nova_floating_ip_list")
            self.collectExtOutput(
                "/usr/bin/nova-manage flavor list 2>/dev/null",
                suggest_filename="nova_flavor_list")
            self.collectExtOutput(
                "/usr/bin/nova-manage network list 2>/dev/null",
                suggest_filename="nova_network_list")
            self.collectExtOutput(
                "/usr/bin/nova-manage vm list 2>/dev/null",
                suggest_filename="nova_vm_list")
        self.addCopySpecs(["/etc/nova/",
                           "/var/log/nova/",
                           "/etc/default/nova-volume",
                           "/etc/sudoers.d/nova_sudoers",
                           "/etc/logrotate.d/nova-*"])
        # Glance
        if os.path.exists("/usr/bin/glance-manage"):
            self.collectExtOutput(
                "/usr/bin/glance-manage db_version",
                suggest_filename="glance_db_version")
        self.addCopySpecs(["/etc/glance/",
                           "/var/log/glance/",
                           "/etc/logrotate.d/glance-*"])
        # Keystone
        self.addCopySpecs(["/etc/keystone/",
                           "/var/log/keystone/",
                           "/etc/logrotate.d/keystone"])
        # Swift
        self.addCopySpecs(["/etc/swift/"])
        # Quantum
        self.addCopySpecs(["/etc/quantum/",
                           "/var/log/quantum/"])


class RedHatOpenStack(openstack, RedHatPlugin):
    """OpenStack related information for Red Hat distributions
    """

    packages = ('openstack-nova',
                'openstack-glance',
                'openstack-dashboard',
                'openstack-keystone',
                'openstack-quantum',
                'openstack-swift',
                'openstack-swift-account',
                'openstack-swift-container',
                'openstack-swift-object',
                'openstack-swift-proxy',
                'swift',
                'python-nova',
                'python-glanceclient',
                'python-keystoneclient',
                'python-novaclient',
                'python-openstackclient',
                'python-quantumclient')

    def setup(self):
        # If RHEL or Fedora then invoke script for openstack-status
        if (os.path.isfile('/etc/redhat-release')
            or os.path.isfile('/etc/fedora-release')):
            self.collectExtOutput("/usr/bin/openstack-status")

        # Nova
        self.addCopySpecs(["/etc/nova/",
                           "/var/log/nova/",
                           "/var/lib/nova/",
                           "/etc/polkit-1/localauthority/50-local.d/50-nova.pkla",
                           "/etc/sudoers.d/nova",
                           "/etc/logrotate.d/openstack-nova"])

        # Glance
        self.addCopySpecs(["/etc/glance/",
                           "/var/log/glance/",
                           "/etc/logrotate.d/openstack-glance"])

        # Keystone
        self.addCopySpecs(["/etc/keystone/",
                           "/var/log/keystone/"])

        # Quantum
        self.addCopySpecs(["/etc/quantum/",
                           "/var/log/quantum/"])
