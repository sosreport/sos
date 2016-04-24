# Copyright (C) 2015 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackSahara(Plugin):
    """OpenStack Sahara"""
    plugin_name = 'openstack_sahara'
    profiles = ('openstack', 'openstack_controller')

    option_list = []

    def setup(self):
        self.add_copy_spec("/etc/sahara/")
        self.add_cmd_output("journalctl -u openstack-sahara-all")
        self.add_cmd_output("journalctl -u openstack-sahara-api")
        self.add_cmd_output("journalctl -u openstack-sahara-engine")

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec_limit("/var/log/sahara/",
                                     sizelimit=self.limit)
        else:
            self.add_copy_spec_limit("/var/log/sahara/*.log",
                                     sizelimit=self.limit)

    def postproc(self):
        protect_keys = [
            "admin_password", "memcache_secret_key", "password",
            "qpid_password", "rabbit_password", "ssl_key_password",
            "xenapi_connection_password", "connection"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/sahara/*", regexp, r"\1*********")


class DebianSahara(OpenStackSahara, DebianPlugin, UbuntuPlugin):
    """OpenStackSahara related information for Debian based distributions."""

    packages = (
        'sahara-api',
        'sahara-common',
        'sahara-engine',
        'python-sahara',
        'python-saharaclient',
    )

    def setup(self):
        super(DebianSahara, self).setup()


class RedHatSahara(OpenStackSahara, RedHatPlugin):
    """OpenStack sahara related information for Red Hat distributions."""

    packages = (
        'openstack-sahara',
        'openstack-sahara-api',
        'openstack-sahara-engine',
        'python-saharaclient'
    )

    def setup(self):
        super(RedHatSahara, self).setup()
        self.add_copy_spec("/etc/sudoers.d/sahara")


# vim: et ts=4 sw=4
