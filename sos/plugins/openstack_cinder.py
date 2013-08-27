## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
## Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>

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

from sos import plugins


class OpenStackCinder(plugins.Plugin):
    """OpenstackCinder related information."""

    plugin_name = "openstack-cinder"

    option_list = [("log", "gathers openstack-cinder logs", "slow", False)]

    def setup(self):
        # Cinder
        self.add_cmd_output(
            "cinder-manage db version",
            suggest_filename="cinder_db_version")
        self.add_copy_specs(["/etc/cinder/",
                             "/var/log/cinder/"])


class DebianOpenStackCinder(OpenStackCinder,
                            plugins.DebianPlugin,
                            plugins.UbuntuPlugin):
    """OpenStackCinder related information for Debian based distributions."""

    packages = ('cinder-api',
                'cinder-backup',
                'cinder-common',
                'cinder-scheduler',
                'cinder-volume',
                'python-cinder',
                'python-cinderclient')

    def setup(self):
        # Cinder
        self.add_copy_spec("/etc/sudoers.d/cinder_sudoers")


class RedHatOpenStackCinder(OpenStackCinder, plugins.RedHatPlugin):
    """OpenStackCinder related information for Red Hat distributions."""

    packages = ('openstack-cinder',
                'python-cinderclient')

    def setup(self):
        # Cinder
        self.add_copy_specs(["/etc/sudoers.d/cinder"])
