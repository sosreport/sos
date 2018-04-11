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

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackSwift(Plugin):
    """OpenStack Swift"""
    plugin_name = "openstack_swift"
    profiles = ('openstack', 'openstack_controller')

    option_list = []

    var_puppet_gen = "/var/lib/config-data/puppet-generated"

    def setup(self):

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/swift/",
                "/var/log/containers/swift/",
                "/var/log/containers/httpd/swift-proxy/"
            ], sizelimit=self.limit)
        else:
            self.add_copy_spec([
                "/var/log/swift/*.log",
                "/var/log/containers/swift/*.log",
                "/var/log/containers/httpd/swift-proxy/*log"
            ], sizelimit=self.limit)

        self.add_copy_spec([
            "/etc/swift/",
            self.var_puppet_gen + "/swift/etc/*",
            self.var_puppet_gen + "/swift/etc/swift/*",
            self.var_puppet_gen + "/swift/etc/xinetd.d/*",
            self.var_puppet_gen + "/memcached/etc/sysconfig/memcached"
        ])

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/swift/.*\.conf.*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/swift/etc/swift/.*\.conf.*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "ldap_dns_password", "neutron_admin_password", "rabbit_password",
            "qpid_password", "powervm_mgr_passwd", "virtual_power_host_pass",
            "xenapi_connection_password", "password", "host_password",
            "vnc_password", "admin_password"
        ]
        connection_keys = ["connection", "sql_connection"]

        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1*********"
        )
        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*(.*)://(\w*):)(.*)(@(.*))" %
            "|".join(connection_keys),
            r"\1*********\6"
        )


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
