# Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
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

from sos import plugins


class OpenStackGlance(plugins.Plugin):
    """OpenstackGlance related information."""
    plugin_name = "openstack-glance"

    option_list = [("log", "gathers openstack-glance logs", "slow", False)]

    def setup(self):
        # Glance
        self.add_cmd_output(
            "glance-manage db_version",
            suggest_filename="glance_db_version"
        )
        self.add_copy_specs([
            "/etc/glance/",
            "/var/log/glance/"
        ])


class DebianOpenStackGlance(OpenStackGlance,
                            plugins.DebianPlugin,
                            plugins.UbuntuPlugin):
    """OpenStackGlance related information for Debian based distributions."""

    packages = (
        'glance',
        'glance-api',
        'glance-client',
        'glance-common',
        'glance-registry',
        'python-glance'
    )


class RedHatOpenStackGlance(OpenStackGlance, plugins.RedHatPlugin):
    """OpenStackGlance related information for Red Hat distributions."""

    packages = (
        'openstack-glance',
        'python-glanceclient'
    )

# vim: et ts=4 sw=4
