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

import sos.plugintools
import os

class ipa(sos.plugintools.PluginBase):
    """IPA diagnostic information
    """

    ipa_server = False
    ipa_client = False

    def checkenabled(self):
        self.ipa_server = self.isInstalled("ipa-server")
        self.ipa_client = self.isInstalled("ipa-client")
        if self.ipa_server or self.ipa_client:
            return True
        return False

    def setup(self):
        self.addCopySpec("/etc/hosts")
        self.addCopySpec("/etc/named.*")
        self.addForbiddenPath("/etc/named.keytab")
        if self.ipa_server:
            self.addCopySpec("/var/log/ipaserver-install.log")
            self.addCopySpec("/var/log/ipareplica-install.log")
        if self.ipa_client:
            self.addCopySpec("/var/log/ipaclient-install.log")

        self.addCopySpec("/var/log/ipaupgrade.log")

        self.addCopySpec("/var/log/krb5kdc.log")
        self.addCopySpec("/var/kerberos/krb5kdc/kdc.conf")

        self.addCopySpec("/var/log/pki-ca/debug")
        self.addCopySpec("/var/log/pki-ca/catalina.out")
        self.addCopySpec("/var/log/pki-ca/system")
        self.addCopySpec("/var/log/pki-ca/transactions")
        self.addForbiddenPath("/etc/pki/nssdb/key*")
        self.addForbiddenPath("/etc/pki-ca/flatfile.txt")
        self.addForbiddenPath("/etc/pki-ca/password.conf")
        self.addForbiddenPath("/var/lib/pki-ca/alias/key*")

        self.addCopySpec("/var/log/dirsrv/slapd-*/logs/access")
        self.addCopySpec("/var/log/dirsrv/slapd-*/logs/errors")
        self.addCopySpec("/etc/dirsrv/slapd-*/dse.ldif")
        self.addCopySpec("/etc/dirsrv/slapd-*/schema/99user.ldif")
        self.addForbiddenPath("/etc/dirsrv/slapd-*/key*")
        self.addForbiddenPath("/etc/dirsrv/slapd-*/pin.txt")
        self.addForbiddenPath("/etc/dirsrv/slapd-*/pwdfile.txt")

        self.collectExtOutput("ls -la /etc/dirsrv/slapd-*/schema/")

        self.collectExtOutput("ipa-getcert list")

        self.collectExtOutput("certutil -L -d /etc/httpd/alias/")
        self.collectExtOutput("certutil -L -d /etc/dirsrv/slapd-*/")

        self.collectExtOutput("klist -ket /etc/dirsrv/ds.keytab")
        self.collectExtOutput("klist -ket /etc/httpd/conf/ipa.keytab")
        self.collectExtOutput("klist -ket /etc/krb5.keytab")

        return


    def postproc(self):
        match = r"(\s*arg \"password )[^\"]*"
        subst = r"\1********"
        self.doRegexSub("/etc/named.conf", match, subst)

