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


class OpenStackKeystone(Plugin):
    """OpenStack Keystone
    """
    plugin_name = "openstack_keystone"
    profiles = ('openstack', 'openstack_controller')

    option_list = [("log", "gathers openstack keystone logs", "slow", True),
                   ("nopw", "dont gathers keystone passwords", "slow", True)]

    def setup(self):
        self.add_copy_spec([
            "/etc/keystone/default_catalog.templates",
            "/etc/keystone/keystone.conf",
            "/etc/keystone/logging.conf",
            "/etc/keystone/policy.json"
        ])

        if self.get_option("log"):
            self.add_copy_spec("/var/log/keystone/")

    def postproc(self):
        protect_keys = [
            "password", "qpid_password", "rabbit_password", "ssl_key_password",
            "ldap_dns_password", "neutron_admin_password", "host_password",
            "connection", "admin_password", "admin_token", "ca_password"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/keystone/*", regexp, r"\1*********")


class DebianKeystone(OpenStackKeystone, DebianPlugin, UbuntuPlugin):

    packages = (
        'keystone',
        'python-keystone',
        'python-keystoneclient'
    )


class RedHatKeystone(OpenStackKeystone, RedHatPlugin):

    packages = (
        'openstack-keystone',
        'python-keystone',
        'python-django-openstack-auth',
        'python-keystoneclient'
    )

# vim: set et ts=4 sw=4 :
