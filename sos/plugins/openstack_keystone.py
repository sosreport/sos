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
    """openstack keystone related information
    """
    plugin_name = "openstack-keystone"

    option_list = [("log", "gathers openstack keystone logs", "slow", True),
                   ("nopw", "dont gathers keystone passwords", "slow", True)]

    def setup(self):
        self.add_copy_specs([
            "/etc/keystone/default_catalog.templates",
            "/etc/keystone/keystone.conf",
            "/etc/keystone/logging.conf",
            "/etc/keystone/policy.json"
        ])

        if self.get_option("log"):
            self.add_copy_spec("/var/log/keystone/")

    def postproc(self):
        self.do_file_sub('/etc/keystone/keystone.conf',
                         r"(?m)^(admin_password.*=)(.*)",
                         r"\1 ******")
        self.do_file_sub('/etc/keystone/keystone.conf',
                         r"(?m)^(admin_token.*=)(.*)",
                         r"\1 ******")
        self.do_file_sub('/etc/keystone/keystone.conf',
                         r"(?m)^(connection.*=.*mysql://)(.*)(:)(.*)(@)(.*)",
                         r"\1\2:******@\6")
        self.do_file_sub('/etc/keystone/keystone.conf',
                         r"(?m)^(password.*=)(.*)",
                         r"\1 ******")
        self.do_file_sub('/etc/keystone/keystone.conf',
                         r"(?m)^(ca_password.*=)(.*)",
                         r"\1 ******")


class DebianOpenStackKeystone(OpenStackKeystone, DebianPlugin, UbuntuPlugin):
    """OpenStack Keystone related information for Debian based distributions
    """

    packages = (
        'keystone',
        'python-keystone',
        'python-keystoneclient'
    )


class RedHatOpenStackKeystone(OpenStackKeystone, RedHatPlugin):
    """OpenStack Keystone related information for Red Hat distributions
    """

    packages = (
        'openstack-keystone',
        'python-keystone',
        'python-django-openstack-auth',
        'python-keystoneclient'
    )

# vim: et ts=4 sw=4
