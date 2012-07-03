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

class openstack(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """openstack related information
    """

    packages = ('openstack-nova',
                'openstack-glance',
                'openstack-dashboard',
                'openstack-keystone',
                'openstack-quantum',
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
