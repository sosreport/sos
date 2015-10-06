# Copyright (C) 2013 Red Hat, Inc.

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


class OpenStackHeat(Plugin):
    """OpenStack Heat
    """
    plugin_name = "openstack_heat"
    profiles = ('openstack', 'openstack_controller')

    option_list = []

    def setup(self):
        # Heat
        self.add_cmd_output(
            "heat-manage db_version",
            suggest_filename="heat_db_version"
        )

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec_limit("/var/log/heat/",
                                     sizelimit=self.limit)
        else:
            self.add_copy_spec_limit("/var/log/heat/*.log",
                                     sizelimit=self.limit)

        self.add_copy_spec("/etc/heat/")

    def postproc(self):
        protect_keys = [
            "admin_password", "memcache_secret_key", "password", "connection",
            "qpid_password", "rabbit_password", "stack_domain_admin_password",
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/heat/*", regexp, r"\1*********")


class DebianHeat(OpenStackHeat, DebianPlugin, UbuntuPlugin):

    packages = (
        'heat-api',
        'heat-api-cfn',
        'heat-api-cloudwatch',
        'heat-common',
        'heat-engine',
        'python-heat',
        'python-heatclient'
    )


class RedHatHeat(OpenStackHeat, RedHatPlugin):

    packages = (
        'openstack-heat-api',
        'openstack-heat-api-cfn',
        'openstack-heat-api-cloudwatch',
        'openstack-heat-cli',
        'openstack-heat-common',
        'openstack-heat-engine',
        'python-heatclient'
    )

# vim: set et ts=4 sw=4 :
