# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
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


class OpenStackCinder(Plugin):
    """openstack cinder related information
    """
    plugin_name = "openstack-cinder"

    option_list = [("log", "gathers openstack cinder logs", "slow", True),
                   ("db", "gathers openstack cinder db version", "slow",
                    False)]

    def setup(self):
        if self.get_option("db"):
            self.add_cmd_output(
                "cinder-manage db version",
                suggest_filename="cinder_db_version")

        self.add_copy_specs(["/etc/cinder/"])

        if self.get_option("log"):
            self.add_copy_specs(["/var/log/cinder/"])


class DebianOpenStackCinder(OpenStackCinder, DebianPlugin, UbuntuPlugin):
    """OpenStack Cinder related information for Debian based distributions
    """

    cinder = False
    packages = (
        'cinder-api',
        'cinder-backup',
        'cinder-common',
        'cinder-scheduler',
        'cinder-volume',
        'python-cinder',
        'python-cinderclient'
    )

    def check_enabled(self):
        self.cinder = self.is_installed("cinder-common")
        return self.cinder

    def setup(self):
        super(DebianOpenStackCinder, self).setup()


class RedHatOpenStackCinder(OpenStackCinder, RedHatPlugin):
    """OpenStack related information for Red Hat distributions
    """

    cinder = False
    packages = ('openstack-cinder',
                'python-cinder',
                'python-cinderclient')

    def check_enabled(self):
        self.cinder = self.is_installed("openstack-cinder")
        return self.cinder

    def setup(self):
        super(RedHatOpenStackCinder, self).setup()
        self.add_copy_specs(["/etc/sudoers.d/cinder"])


# vim: et ts=4 sw=4
