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
    profiles = ('openstack',)
    option_list = [("log", "gathers openstack trove logs", "slow", True)]

    def setup(self):
        self.add_copy_spec('/etc/trove/')

        if self.get_option('log'):
            self.add_copy_spec('/var/log/trove')

    def postproc(self):

        protect_keys = [
            "dns_passkey", "nova_proxy_admin_pass", "rabbit_password",
            "qpid_password", "connection", "sql_connection", "admin_password"
        ]

        conf_list = [
            '/etc/trove/trove.conf',
            '/etc/trove/trove-conductor.conf',
            '/etc/trove/trove-guestmanager.conf',
            '/etc/trove/trove-taskmanager.conf'
        ]

        regexp = r"((?m)^\s*#*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)

        for conf in conf_list:
            self.do_file_sub(conf, regexp, r"\1*********")


class DebianOpenStackTrove(OpenStackTrove, DebianPlugin, UbuntuPlugin):

    packages = [
        'python-trove',
        'trove-common',
        'trove-api',
        'trove-taskmanager'
    ]

    def setup(self):
        super(DebianOpenStackTrove, self).setup()


class RedHatOpenStackTrove(OpenStackTrove, RedHatPlugin):

    packages = ['openstack-trove']

    def setup(self):
        super(RedHatOpenStackTrove, self).setup()

# vim: et ts=4 sw=4
