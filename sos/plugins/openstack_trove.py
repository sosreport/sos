# Copyright (C) 2015 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>

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


class OpenStackTrove(Plugin):
    """OpenStack Trove
    """

    plugin_name = "openstack_trove"
    profiles = ('openstack', 'openstack_controller')
    option_list = []

    def setup(self):

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec_limit("/var/log/trove/",
                                     sizelimit=self.limit)
        else:
            self.add_copy_spec_limit("/var/log/trove/*.log",
                                     sizelimit=self.limit)

        self.add_copy_spec('/etc/trove/')

    def postproc(self):

        protect_keys = [
            "default_password_length", "notifier_queue_password",
            "rabbit_password", "replication_password", "connection",
            "admin_password", "dns_passkey"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/trove/*", regexp, r"\1*********")


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
