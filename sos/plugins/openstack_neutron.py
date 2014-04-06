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


class OpenStackNeutron(Plugin):
    """openstack neutron related information
    """
    plugin_name = "openstack-neutron"

    option_list = [("log", "gathers openstack neutron logs", "slow", True)]

    def setup(self):
        self.add_copy_spec("/etc/neutron/")

        if self.option_enabled("log"):
            self.add_copy_spec("/var/log/neutron/")


class DebianOpenStackNeutron(OpenStackNeutron, DebianPlugin, UbuntuPlugin):
    """OpenStack Neutron related information for Debian based distributions
    """

    neutron = False
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
        self.neutron = self.is_installed("neutron-common")
        return self.neutron

    def setup(self):
        super(DebianOpenStackNeutron, self).setup()
        self.add_copy_specs(["/etc/sudoers.d/neutron_sudoers"])


class RedHatOpenStackNeutron(OpenStackNeutron, RedHatPlugin):
    """OpenStack Neutron related information for Red Hat distributions
    """

    neutron = False
    packages = (
        'openstack-neutron-bigswitch',
        'openstack-neutron-brocade',
        'openstack-neutron-cisco',
        'openstack-neutron-hyperv',
        'openstack-neutron-linuxbridge',
        'openstack-neutron-metaplugin',
        'openstack-neutron-midonet',
        'openstack-neutron-nec',
        'openstack-neutron-nicira',
        'openstack-neutron-openvswitch',
        'openstack-neutron-plumgrid',
        'openstack-neutron-ryu',
        'python-neutron',
        'python-neutronclient',
        'openstack-neutron'
    )

    def check_enabled(self):
        self.neutron = self.is_installed("openstack-neutron")
        return self.neutron

    def setup(self):
        super(RedHatOpenStackNeutron, self).setup()

# vim: et ts=4 sw=4
