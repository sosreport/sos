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

    def setup(self):
        # Glance
        self.add_cmd_output(
            "glance-manage db_version",
            suggest_filename="glance_db_version")
        self.add_copy_specs(["/etc/glance/",
                           "/var/log/glance/"])

        # Cinder
        self.add_cmd_output(
            "cinder-manage db version",
            suggest_filename="cinder_db_version")
        self.add_copy_specs(["/etc/cinder/",
                           "/var/log/cinder/"])

        # Keystone
        self.add_copy_specs(["/etc/keystone/",
                           "/var/log/keystone/"])

        # Quantum
        self.add_copy_specs(["/etc/quantum/",
                           "/var/log/quantum/"])

        # Swift
        self.add_copy_spec("/etc/swift/")

    def postproc(self):
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(admin_password\s*=\s*)(.*)",
                    r"\1******")


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
                'python-quantum',
                'python-quantumclient',
                'python-swift',
                'python-swauth')

    def setup(self):
        # Cinder
        self.add_copy_spec("/etc/sudoers.d/cinder_sudoers")

        # Quantum
        self.add_copy_spec("/etc/sudoers.d/quantum_sudoers")


class RedHatOpenStack(OpenStack, RedHatPlugin):
    """OpenStack related information for Red Hat distributions
    """

    packages = ('openstack-glance',
                'openstack-dashboard',
                'openstack-keystone',
                'openstack-quantum',
                'openstack-swift',
                'openstack-swift-account',
                'openstack-swift-container',
                'openstack-swift-object',
                'openstack-swift-proxy',
                'swift',
                'python-glanceclient',
                'python-keystoneclient',
                'python-openstackclient',
                'python-quantumclient')
