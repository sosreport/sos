# Copyright (C) 2015 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>

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


class OpenStackTrove(Plugin):
    """OpenStack Trove
    """

    plugin_name = "openstack_trove"
    profiles = ('openstack', 'openstack_controller')
    option_list = []

    var_puppet_gen = "/var/lib/config-data/puppet-generated/trove"

    def setup(self):

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/trove/",
                "/var/log/containers/trove/"
            ], sizelimit=self.limit)
        else:
            self.add_copy_spec([
                "/var/log/trove/*.log",
                "/var/log/containers/trove/*.log"
            ], sizelimit=self.limit)

        self.add_copy_spec([
            '/etc/trove/',
            self.var_puppet_gen + '/etc/trove/'
        ])

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/trove/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/trove/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "default_password_length", "notifier_queue_password",
            "rabbit_password", "replication_password", "admin_password",
            "dns_passkey"
        ]
        connection_keys = ["connection"]

        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1*********"
        )
        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*(.*)://(\w*):)(.*)(@(.*))" %
            "|".join(connection_keys),
            r"\1*********\6"
        )


class DebianTrove(OpenStackTrove, DebianPlugin, UbuntuPlugin):

    packages = [
        'python-trove',
        'trove-common',
        'trove-api',
        'trove-taskmanager'
    ]

    def setup(self):
        super(DebianTrove, self).setup()


class RedHatTrove(OpenStackTrove, RedHatPlugin):

    packages = ['openstack-trove']

    def setup(self):
        super(RedHatTrove, self).setup()

# vim: set et ts=4 sw=4 :
