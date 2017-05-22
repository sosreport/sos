# Copyright (C) 2016 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

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


class OpenStackManila(Plugin):
    """OpenStack Manila
    """
    plugin_name = "openstack_manila"
    profiles = ('openstack', 'openstack_controller')
    option_list = []

    def setup(self):
        self.add_copy_spec("/etc/manila/")

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/manila/*",
                               sizelimit=self.limit)
        else:
            self.add_copy_spec("/var/log/manila/*.log",
                               sizelimit=self.limit)

    def postproc(self):
        protect_keys = [
            "nova_admin_password",  "rabbit_password",  "qpid_password",
            "password", "netapp_nas_password", "cinder_admin_password",
            "neutron_admin_password", "service_instance_password",
            "connection", "sql_connection"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/manila/*", regexp, r"\1*********")


class DebianManila(OpenStackManila, DebianPlugin, UbuntuPlugin):
    """OpenStackManila related information for Debian based distributions."""

    packages = (
        'python-manila',
        'manila-common',
        'manila-api',
        'manila-share',
        'manila-scheduler'
    )


class RedHatManila(OpenStackManila, RedHatPlugin):
    """OpenStackManila related information for Red Hat distributions."""

    packages = (
        'puppet-manila',
        'openstack-manila',
        'openstack-manila-share',
        'python-manila',
        'python-manilaclient',
        'python-manila-tests'
    )

    def setup(self):
        super(RedHatManila, self).setup()
        self.add_copy_spec("/etc/sudoers.d/manila")


# vim: et ts=4 sw=4
