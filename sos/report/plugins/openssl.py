# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenSSL(Plugin):

    short_desc = 'OpenSSL configuration'

    plugin_name = "openssl"
    profiles = ('network', 'security')
    packages = ('openssl',)
    verify_packages = ('openssl.*',)

    def postproc(self):
        protect_keys = [
            "input_password",
            "output_password",
            "challengePassword"
        ]

        regexp = r"(?m)^(\s*#?\s*(%s).*=)(.*)" % "|".join(protect_keys)

        self.do_file_sub(
            '/etc/ssl/openssl.cnf',
            regexp,
            r"\1 ******"
        )


class RedHatOpenSSL(OpenSSL, RedHatPlugin):

    files = ('/etc/pki/tls/openssl.cnf',)

    def setup(self):
        super(RedHatOpenSSL, self).setup()
        self.add_copy_spec("/etc/pki/tls/openssl.cnf")


class DebianOpenSSL(OpenSSL, DebianPlugin, UbuntuPlugin):

    files = ('/etc/ssl/openssl.cnf',)

    def setup(self):
        super(DebianOpenSSL, self).setup()
        self.add_copy_spec("/etc/ssl/openssl.cnf")

# vim: set et ts=4 sw=4 :
