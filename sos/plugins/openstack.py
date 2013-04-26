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


class OpenStack(Plugin):
    """openstack related information
    """
    plugin_name = "openstack"

    option_list = [("log", "gathers all openstack logs", "slow", False)]


class DebianOpenStack(OpenStack, DebianPlugin, UbuntuPlugin):
    """OpenStack related information for Debian based distributions
    """

    packages = ('cinder-api',
                'cinder-backup',
                'cinder-common',
                'cinder-scheduler',
                'cinder-volume',
                'glance',
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
                'python-cinder',
                'python-cinderclient',
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
        if os.path.exists("nova-manage"):
            self.add_cmd_output(
                "nova-manage config list 2>/dev/null | sort",
                suggest_filename="nova_config_list")
            self.add_cmd_output(
                "nova-manage service list 2>/dev/null",
                suggest_filename="nova_service_list")
            self.add_cmd_output(
                "nova-manage db version 2>/dev/null",
                suggest_filename="nova_db_version")
            self.add_cmd_output(
                "nova-manage fixed list 2>/dev/null",
                suggest_filename="nova_fixed_ip_list")
            self.add_cmd_output(
                "nova-manage floating list 2>/dev/null",
                suggest_filename="nova_floating_ip_list")
            self.add_cmd_output(
                "nova-manage flavor list 2>/dev/null",
                suggest_filename="nova_flavor_list")
            self.add_cmd_output(
                "nova-manage network list 2>/dev/null",
                suggest_filename="nova_network_list")
            self.add_cmd_output(
                "nova-manage vm list 2>/dev/null",
                suggest_filename="nova_vm_list")
        self.add_copy_specs(["/etc/nova/",
                           "/var/log/nova/",
                           "/etc/default/nova-volume",
                           "/etc/sudoers.d/nova_sudoers",
                           "/etc/logrotate.d/nova-*"])
        # Cinder
        if os.path.exists("/usr/bin/cinder-manage"):
            self.addCmdOutput(
                "/usr/bin/cinder-manage db version",
                suggest_filename="cinder_db_version")
        self.addCopySpecs(["/etc/cinder/",
                           "/var/log/cinder/",
                           "/etc/logrotate.d/cinder-*"])
        # Glance
        if os.path.exists("glance-manage"):
            self.add_cmd_output(
                "glance-manage db_version",
                suggest_filename="glance_db_version")
        self.add_copy_specs(["/etc/glance/",
                           "/var/log/glance/",
                           "/etc/logrotate.d/glance-*"])
        # Keystone
        self.add_copy_specs(["/etc/keystone/",
                           "/var/log/keystone/",
                           "/etc/logrotate.d/keystone"])
        # Swift
        self.add_copy_specs(["/etc/swift/"])
        # Quantum
        self.add_copy_specs(["/etc/quantum/",
                           "/var/log/quantum/"])


class RedHatOpenStack(OpenStack, RedHatPlugin):
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
            self.add_cmd_output("openstack-status")

        # Nova
        self.add_copy_specs(["/etc/nova/",
                           "/var/log/nova/",
                           "/var/lib/nova/",
                           "/etc/polkit-1/localauthority/50-local.d/50-nova.pkla",
                           "/etc/sudoers.d/nova",
                           "/etc/logrotate.d/openstack-nova"])

        # Glance
        self.add_copy_specs(["/etc/glance/",
                           "/var/log/glance/",
                           "/etc/logrotate.d/openstack-glance"])

        # Keystone
        self.add_copy_specs(["/etc/keystone/",
                           "/var/log/keystone/"])

        # Quantum
        self.add_copy_specs(["/etc/quantum/",
                           "/var/log/quantum/"])

    def postproc(self):
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(admin_password\s*=\s*)(.*)",
                    r"\1******")
