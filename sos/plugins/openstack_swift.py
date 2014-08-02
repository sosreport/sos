# Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#               Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>

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


class OpenStackSwift(Plugin):
    """OpenstackSwift related information."""
    plugin_name = "openstack-swift"

    option_list = [("log", "gathers openstack-swift logs", "slow", False)]

    def setup(self):
        # Swift
        self.add_copy_spec("/etc/swift/")


class DebianOpenStackSwift(OpenStackSwift, DebianPlugin, UbuntuPlugin):
    """OpenStackSwift related information for Debian based distributions."""

    packages = (
        'swift',
        'swift-account',
        'swift-container',
        'swift-object',
        'swift-proxy',
        'swauth',
        'python-swift',
        'python-swauth'
    )


class RedHatOpenStackSwift(OpenStackSwift, RedHatPlugin):
    """OpenStackSwift related information for Red Hat distributions."""

    packages = (
        'openstack-swift',
        'openstack-swift-account',
        'openstack-swift-container',
        'openstack-swift-object',
        'openstack-swift-proxy',
        'swift',
        'python-swiftclient'
    )

# vim: et ts=4 sw=4
