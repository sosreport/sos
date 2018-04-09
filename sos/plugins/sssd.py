# Copyright (C) 2007 Red Hat, Inc., Pierre Carrier <pcarrier@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
