# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackHorizon(Plugin):
    """openstack horizon related information
    """

    plugin_name = "openstack-horizon"
    option_list = [("log", "gathers openstack horizon logs", "slow", True)]

    def setup(self):
        self.add_copy_spec("/etc/openstack-dashboard/")
        if self.get_option("log"):
            self.add_copy_spec("/var/log/horizon/")


class DebianOpenStackHorizon(OpenStackHorizon, DebianPlugin):
    """OpenStack Horizon related information for Debian based distributions
    """

    packages = (
        'python-django-horizon',
        'openstack-dashboard',
        'openstack-dashboard-apache'
    )

    def setup(self):
        super(DebianOpenStackHorizon, self).setup()
        self.add_copy_spec("/etc/apache2/sites-available/")


class UbuntuOpenStackHorizon(OpenStackHorizon, UbuntuPlugin):
    """OpenStack Horizon related information for Ubuntu based distributions
    """

    packages = (
        'python-django-horizon',
        'openstack-dashboard',
        'openstack-dashboard-ubuntu-theme'
    )

    def setup(self):
        super(UbuntuOpenStackHorizon, self).setup()
        self.add_copy_spec("/etc/apache2/conf.d/openstack-dashboard.conf")


class RedHatOpenStackHorizon(OpenStackHorizon, RedHatPlugin):
    """OpenStack Horizon related information for Red Hat distributions
    """

    packages = (
        'python-django-horizon',
        'openstack-dashboard'
    )

    def setup(self):
        super(RedHatOpenStackHorizon, self).setup()
        self.add_copy_spec("/etc/httpd/conf.d/openstack-dashboard.conf")
        if self.get_option("log"):
            self.add_copy_spec("/var/log/httpd/")

# vim: et ts=4 sw=4
