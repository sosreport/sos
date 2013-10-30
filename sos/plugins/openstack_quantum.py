## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
## Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

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


class OpenStackQuantum(Plugin):
    """openstack quantum related information
    """
    plugin_name = "openstack-quantum"

    option_list = [("log", "gathers openstack quantum logs", "slow", True)]

    def setup(self):
        self.add_copy_specs(["/etc/quantum/"])

        if self.option_enabled("log"):
            self.add_copy_specs(["/var/log/quantum/"])


class DebianOpenStackQuantum(OpenStackQuantum, DebianPlugin, UbuntuPlugin):
    """OpenStack Quantum related information for Debian based distributions
    """

    quantum = False
    packages = ('quantum-common',
                'quantum-plugin-cisco',
                'quantum-plugin-linuxbridge-agent',
                'quantum-plugin-nicira',
                'quantum-plugin-openvswitch',
                'quantum-plugin-openvswitch-agent',
                'quantum-plugin-ryu',
                'quantum-plugin-ryu-agent',
                'quantum-server',
                'python-quantum',
                'python-quantumclient')

    def check_enabled(self):
        self.quantum = self.is_installed("quantum-common")
        return self.quantum

    def setup(self):
        super(DebianOpenStackQuantum, self).setup()
        self.add_copy_specs(["/etc/sudoers.d/quantum_sudoers"])


class RedHatOpenStackQuantum(OpenStackQuantum, RedHatPlugin):
    """OpenStack Quantum related information for Red Hat distributions
    """

    quantum = False
    packages = ('openstack-quantum-bigswitch',
                'openstack-quantum-brocade',
                'openstack-quantum-cisco',
                'openstack-quantum-hyperv',
                'openstack-quantum-linuxbridge',
                'openstack-quantum-metaplugin',
                'openstack-quantum-midonet',
                'openstack-quantum-nec',
                'openstack-quantum-nicira',
                'openstack-quantum-openvswitch',
                'openstack-quantum-plumgrid',
                'openstack-quantum-ryu',
                'python-quantum',
                'python-quantumclient',
                'openstack-quantum')

    def check_enabled(self):
        self.quantum = self.is_installed("openstack-quantum")
        return self.quantum

    def setup(self):
        super(RedHatOpenStackQuantum, self).setup()
