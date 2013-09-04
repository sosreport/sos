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


class OpenStackKeystone(Plugin):
    """openstack keystone related information
    """
    plugin_name = "openstack-keystone"

    option_list = [("log", "gathers openstack keystone logs", "slow", True)]

    def setup(self):
        self.add_copy_specs(["/etc/keystone/"])

        if self.option_enabled("log"):
            self.add_copy_specs(["/var/log/keystone/"])

    def postproc(self):
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(admin_password\s*=\s*)(.*)",
                    r"\1******")
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(admin_token\s*=\s*)(.*)",
                    r"\1******")
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(connection\s*=\s*mysql://)(.*)(:)(.*)(@)(.*)",
                    r"\1\2:******@\6")
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(password\s*=\s*)(.*)",
                    r"\1******")

class DebianOpenStackKeystone(OpenStackKeystone, DebianPlugin, UbuntuPlugin):
    """OpenStack Keystone related information for Debian based distributions
    """

    keystone = False
    packages = ('keystone',
                'python-keystone',
                'python-keystoneclient')

    def check_enabled(self):
        self.keystone = self.is_installed("keystone")
        return self.keystone

    def setup(self):
        super(DebianOpenStackKeystone, self).setup()

class RedHatOpenStackKeystone(OpenStackKeystone, RedHatPlugin):
    """OpenStack Keystone related information for Red Hat distributions
    """

    keystone = False
    packages = ('openstack-keystone',
                'python-keystone',
                'python-django-openstack-auth',
                'python-keystoneclient')

    def check_enabled(self):
        self.keystone = self.is_installed("openstack-keystone")
        return self.keystone

    def setup(self):
        super(RedHatOpenStackKeystone, self).setup()
