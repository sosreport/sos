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


class OpenStackDashboard(Plugin):
    """openstack dashboard related information
    """
    plugin_name = "openstack-dashboard"

    option_list = [("log", "gathers openstack httpd logs", "slow", True)]

    def setup(self):
        self.add_copy_specs(["/etc/openstack-dashboard/"])


class DebianOpenStackDashboard(OpenStackDashboard, DebianPlugin):
    """OpenStack related information for Debian based distributions
    """

    packages = ('openstack-dashboard',
                'openstack-dashboard-apache')
    dashboard = False

    def check_enabled(self):
        self.dashboard = self.is_installed("openstack-dashboard")
        return self.dashboard

    def setup(self):
        super(DebianOpenStackDashboard, self).setup()
        self.add_copy_specs(["/etc/apache2/sites-available/"])

class UbuntuOpenStackDashboard(OpenStackDashboard, UbuntuPlugin):
    """OpenStack related information for Ubuntu based distributions
    """

    packages = ('openstack-dashboard',
                'openstack-dashboard-ubuntu-theme')
    dashboard = False

    def check_enabled(self):
        self.dashboard = self.is_installed("openstack-dashboard")
        return self.dashboard

    def setup(self):
        super(UbuntuOpenStackDashboard, self).setup()
        self.add_copy_specs(["/etc/apache2/conf.d/openstack-dashboard.conf"])

class RedHatOpenStackDashboard(OpenStackDashboard, RedHatPlugin):
    """OpenStack related information for Red Hat distributions
    """

    dashboard = False
    packages = ('openstack-dashboard')

    def check_enabled(self):
        self.dashboard = self.is_installed("openstack-dashboard")
        return self.dashboard

    def setup(self):
        super(RedHatOpenStackDashboard, self).setup()
        self.add_copy_specs(["/etc/httpd/conf.d/openstack-dashboard.conf"])
        if self.option_enabled("log"):
            self.add_copy_specs(["/var/log/httpd/"])
