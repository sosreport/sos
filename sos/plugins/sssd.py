# Copyright (C) 2007 Red Hat, Inc., Pierre Carrier <pcarrier@redhat.com>

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


class Sssd(Plugin):
    """System security service daemon
    """

    plugin_name = "sssd"
    profiles = ('services', 'security', 'identity')
    packages = ('sssd',)

    def setup(self):
        self.add_copy_spec([
            "/etc/sssd/sssd.conf",
            "/var/log/sssd/*",
            "/var/lib/sss/pubconf/krb5.include.d/*",
            # SSSD 1.14
            "/etc/sssd/conf.d/*.conf"
        ])

        self.add_cmd_output("sssctl config-check")

        domain_file = self.get_cmd_output_now("sssctl domain-list")
        if domain_file:
            for domain_name in open(domain_file).read().splitlines():
                self.add_cmd_output("sssctl domain-status -o "+domain_name)

    def postproc(self):
        regexp = r"(\s*ldap_default_authtok\s*=\s*)\S+"

        self.do_file_sub("/etc/sssd/sssd.conf", regexp, r"\1********")
        self.do_path_regex_sub("/etc/sssd/conf.d/*", regexp, r"\1********")


class RedHatSssd(Sssd, RedHatPlugin):

    def setup(self):
        super(RedHatSssd, self).setup()


class DebianSssd(Sssd, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianSssd, self).setup()
        self.add_copy_spec("/etc/default/sssd")

# vim: set et ts=4 sw=4 :
