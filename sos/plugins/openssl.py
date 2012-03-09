## Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class openssl(Plugin):
    """openssl related information
    """

    plugin_name = "openssl"
    packages = ('openssl',)

class RedHatOpenssl(openssl, RedHatPlugin):
    """openssl related information for Red Hat distributions
    """

    files = ('/etc/pki/tls/openssl.cnf',)

    def setup(self):
        super(RedHatOpenssl, self).setup()
        self.addCopySpec("/etc/pki/tls/openssl.cnf")

class DebianOpenssl(openssl, DebianPlugin, UbuntuPlugin):
    """openssl related information for Debian distributions
    """

    files = ('/etc/ssl/openssl.cnf',)

    def setup(self):
        super(DebianOpenssl, self).setup()
        self.addCopySpec("/etc/ssl/openssl.cnf")
