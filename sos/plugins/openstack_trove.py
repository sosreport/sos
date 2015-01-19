# Copyright (C) 2015 Red Hat, Inc., Swapnil Kulkarni <skulkarn@redhat.com>
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


class OpenStackTrove(Plugin):
    """OpenStack Trove
    """
    plugin_name = "openstack_trove"
    profiles = ('openstack',)

    option_list = [("log", "gathers openstack trove logs", "slow", True)]

    def setup(self):
        self.add_copy_spec(["/etc/trove/"])

        if self.get_option("log"):
            self.add_copy_spec(["/var/log/trove/"])


class DebianOpenStackTrove(OpenStackTrove, DebianPlugin, UbuntuPlugin):

    trove = False
    packages = (
        'trove-api',
        'trove-common',
        'trove-conductor',
        'trove-doc',
        'trove-guestagent',
        'trove-taskmanager',
        'python-trove',
        'python-troveclient'
    )

    def setup(self):
        super(DebianOpenStackTrove, self).setup()


class RedHatOpenStackTrove(OpenStackTrove, RedHatPlugin):

    trove = False
    packages = (
        'openstack-trove',
        'openstack-trove-api',
        'openstack-trove-common',
        'openstack-trove-conductor',
        'openstack-trove-guestagent',
        'openstack-trove-taskmanager',
        'python-trove',
        'python-troveclient'
    )

    def setup(self):
        super(RedHatOpenStackTrove, self).setup()
        self.add_copy_spec(["/etc/sudoers.d/trove"])


# vim: et ts=4 sw=4
