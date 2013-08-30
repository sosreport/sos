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


class OpenStackSwift(Plugin):
    """openstack swift related information
    """
    plugin_name = "openstack-swift"

    option_list = [("log", "gathers openstack swift logs", "slow", True)]

    def setup(self):
        if self.option_enabled("log"):
            self.add_copy_specs(["/etc/swift/"])


class DebianOpenStackSwift(OpenStackSwift, DebianPlugin, UbuntuPlugin):
    """OpenStack related information for Debian based distributions
    """

    swift = False
    packages = ('swift',
                'swift-account',
                'swift-container',
                'swift-object',
                'swift-proxy',
                'swauth',
                'python-swift',
                'python-swauth')

    def check_enabled(self):
        self.swift = self.is_installed("swift")
        return self.swift

    def setup(self):
        super(DebianOpenStackSwift, self).setup()


class RedHatOpenStackSwift(OpenStackSwift, RedHatPlugin):
    """OpenStack related information for Red Hat distributions
    """

    swift = False
    packages = ('openstack-swift',
                'openstack-swift-account',
                'openstack-swift-container',
                'openstack-swift-object',
                'openstack-swift-plugin-swift3',
                'openstack-swift-proxy',
                'python-swiftclient')

    def check_enabled(self):
        self.swift = self.is_installed("openstack-swift")
        return self.swift

    def setup(self):
        super(RedHatOpenStackSwift, self).setup()
        if self.option_enabled("log"):
            self.add_copy_specs(["/var/log/swift-startup.log"])