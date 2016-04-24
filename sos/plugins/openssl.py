# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

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


class OpenSSL(Plugin):
    """OpenSSL configuration
    """

    plugin_name = "openssl"
    profiles = ('network', 'security')
    packages = ('openssl',)

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
    """openssl related information
    """

    files = ('/etc/pki/tls/openssl.cnf',)

    def setup(self):
        super(RedHatOpenSSL, self).setup()
        self.add_copy_spec("/etc/pki/tls/openssl.cnf")


class DebianOpenSSL(OpenSSL, DebianPlugin, UbuntuPlugin):
    """openssl related information for Debian distributions
    """

    files = ('/etc/ssl/openssl.cnf',)

    def setup(self):
        super(DebianOpenSSL, self).setup()
        self.add_copy_spec("/etc/ssl/openssl.cnf")

# vim: set et ts=4 sw=4 :
