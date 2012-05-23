## Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>

## This program is free software; you can redistribute it and/or modify
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

from sos.plugins import Plugin, RedHatPlugin
from os.path import exists

class ipa(Plugin, RedHatPlugin):
    """IPA diagnostic information
    """

    ipa_server = False
    ipa_client = False

    files = ('/etc/ipa',)
    packages = ('ipa-server', 'ipa-client')

    def checkenabled(self):
        self.ipa_server = self.isInstalled("ipa-server")
        self.ipa_client = self.isInstalled("ipa-client")
        return Plugin.checkenabled(self)

    def setup(self):
        if self.ipa_server:
            self.addCopySpec("/var/log/ipaserver-install.log")
            self.addCopySpec("/var/log/ipareplica-install.log")
        if self.ipa_client:
            self.addCopySpec("/var/log/ipaclient-install.log")

        self.addCopySpecs(["/var/log/ipaupgrade.log",
                        "/var/log/krb5kdc.log",
                        "/var/log/pki-ca/debug",
                        "/var/log/pki-ca/catalina.out",
                        "/var/log/pki-ca/system",
                        "/var/log/pki-ca/transactions",
                        "/var/log/dirsrv/slapd-*/logs/access",
                        "/var/log/dirsrv/slapd-*/logs/errors",
                        "/etc/dirsrv/slapd-*/dse.ldif",
                        "/etc/dirsrv/slapd-*/schema/99user.ldif",
                        "/etc/hosts",
                        "/etc/named.*"])
 
        self.addForbiddenPath("/etc/pki/nssdb/key*")
        self.addForbiddenPath("/etc/pki-ca/flatfile.txt")
        self.addForbiddenPath("/etc/pki-ca/password.conf")
        self.addForbiddenPath("/var/lib/pki-ca/alias/key*")

        self.addForbiddenPath("/etc/dirsrv/slapd-*/key*")
        self.addForbiddenPath("/etc/dirsrv/slapd-*/pin.txt")
        self.addForbiddenPath("/etc/dirsrv/slapd-*/pwdfile.txt")

        self.addForbiddenPath("/etc/named.keytab")

        self.collectExtOutput("ls -la /etc/dirsrv/slapd-*/schema/")

        self.collectExtOutput("ipa-getcert list")

        self.collectExtOutput("certutil -L -d /etc/httpd/alias/")
        self.collectExtOutput("certutil -L -d /etc/dirsrv/slapd-*/")

        self.collectExtOutput("klist -ket /etc/dirsrv/ds.keytab")
        self.collectExtOutput("klist -ket /etc/httpd/conf/ipa.keytab")
        self.collectExtOutput("klist -ket /etc/krb5.keytab")

        return
