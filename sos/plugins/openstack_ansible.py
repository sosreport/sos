# Copyright (C) 2017 Major Hayden <major@mhtx.net>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackAnsible(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """OpenStack-Ansible sos plugin."""

    plugin_name = "openstack_ansible"
    profiles = ('openstack',)
    files = ('/etc/openstack_deploy/',)

    def setup(self):
        """Gathering the contents of the report."""
        self.add_copy_spec([
            "/etc/openstack_deploy/",
            "/etc/openstack-release",
            "/etc/rpc_deploy/",
            "/etc/rpc-release"
        ])

    def postproc(self):
        """Remove sensitive keys and passwords from YAML files."""
        secrets_files = [
            "/etc/openstack_deploy/user_secrets.yml",
            "/etc/rpc_deploy/user_secrets.yml"
        ]
        regexp = r"(?m)^\s*#*([\w_]*:\s*).*"
        for secrets_file in secrets_files:
            self.do_path_regex_sub(
                secrets_file,
                regexp,
                r"\1*********")
