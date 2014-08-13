# Copyright (C) 2013 Red Hat, Inc., Eoghan Lynn <eglynn@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.
#               2012 Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2009 Red Hat, Inc.
#               2009 Joey Boggs <jboggs@redhat.com>

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


class OpenStackCeilometer(Plugin):
    """Openstack Ceilometer related information."""
    plugin_name = "openstack-ceilometer"

    option_list = [("log", "gathers openstack-ceilometer logs", "slow", False)]

    def setup(self):
        # Ceilometer
        self.add_copy_specs([
            "/etc/ceilometer/",
            "/var/log/ceilometer"
        ])


class DebianOpenStackCeilometer(OpenStackCeilometer, DebianPlugin,
                                UbuntuPlugin):
    """OpenStackCeilometer related information for Debian based distributions.
    """

    packages = (
        'ceilometer-api',
        'ceilometer-agent-central',
        'ceilometer-agent-compute',
        'ceilometer-collector',
        'ceilometer-common',
        'python-ceilometer',
        'python-ceilometerclient'
    )


class RedHatOpenStackCeilometer(OpenStackCeilometer, RedHatPlugin):
    """OpenStackCeilometer related information for Red Hat distributions."""

    packages = (
        'openstack-ceilometer',
        'openstack-ceilometer-api',
        'openstack-ceilometer-central',
        'openstack-ceilometer-collector',
        'openstack-ceilometer-common',
        'openstack-ceilometer-compute',
        'python-ceilometerclient'
    )

# vim: et ts=4 sw=4
