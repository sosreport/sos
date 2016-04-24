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
    """OpenStack Swift"""
    plugin_name = "openstack_swift"
    profiles = ('openstack', 'openstack_controller')

    option_list = []

    def setup(self):

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec_limit("/var/log/swift/",
                                     sizelimit=self.limit)
        else:
            self.add_copy_spec_limit("/var/log/swift/*.log",
                                     sizelimit=self.limit)

        self.add_copy_spec("/etc/swift/")

    def postproc(self):
        protect_keys = [
            "ldap_dns_password", "neutron_admin_password", "rabbit_password",
            "qpid_password", "powervm_mgr_passwd", "virtual_power_host_pass",
            "xenapi_connection_password", "password", "host_password",
            "vnc_password", "connection", "sql_connection", "admin_password"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/swift/.*\.conf.*", regexp, r"\1*********")


class DebianSwift(OpenStackSwift, DebianPlugin, UbuntuPlugin):

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


class RedHatSwift(OpenStackSwift, RedHatPlugin):

    packages = (
        'openstack-swift',
        'openstack-swift-account',
        'openstack-swift-container',
        'openstack-swift-object',
        'openstack-swift-proxy',
        'swift',
        'python-swiftclient'
    )

# vim: set et ts=4 sw=4 :
