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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackGlance(Plugin):
    """OpenStack Glance"""
    plugin_name = "openstack_glance"
    profiles = ('openstack', 'openstack_controller')

    option_list = []

    def setup(self):
        # Glance
        self.add_cmd_output(
            "glance-manage db_version",
            suggest_filename="glance_db_version"
        )

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec_limit("/var/log/glance/",
                                     sizelimit=self.limit)
        else:
            self.add_copy_spec_limit("/var/log/glance/*.log",
                                     sizelimit=self.limit)

        self.add_copy_spec("/etc/glance/")

    def postproc(self):
        protect_keys = [
            "admin_password", "password", "qpid_password", "rabbit_password",
            "s3_store_secret_key", "ssl_key_password", "connection",
            "vmware_server_password"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/glance/*", regexp, r"\1*********")


class DebianGlance(OpenStackGlance, DebianPlugin, UbuntuPlugin):

    packages = (
        'glance',
        'glance-api',
        'glance-client',
        'glance-common',
        'glance-registry',
        'python-glance'
    )


class RedHatGlance(OpenStackGlance, RedHatPlugin):

    packages = (
        'openstack-glance',
        'python-glanceclient'
    )

# vim: set et ts=4 sw=4 :
