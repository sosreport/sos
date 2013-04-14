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

class Ipa(Plugin, RedHatPlugin):
    """IPA diagnostic information
    """

    ipa_server = False
    ipa_client = False

    files = ('/etc/ipa',)
    packages = ('ipa-server', 'ipa-client')

    def check_enabled(self):
        self.ipa_server = self.is_installed("ipa-server")
        self.ipa_client = self.is_installed("ipa-client")
        return Plugin.check_enabled(self)

    def setup(self):
        if self.ipa_server:
            self.add_copy_spec("/var/log/ipaserver-install.log")
            self.add_copy_spec("/var/log/ipareplica-install.log")
        if self.ipa_client:
            self.add_copy_spec("/var/log/ipaclient-install.log")

        self.add_copy_specs(["/var/log/ipaupgrade.log",
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
 
        self.add_forbidden_path("/etc/pki/nssdb/key*")
        self.add_forbidden_path("/etc/pki-ca/flatfile.txt")
        self.add_forbidden_path("/etc/pki-ca/password.conf")
        self.add_forbidden_path("/var/lib/pki-ca/alias/key*")

        self.add_forbidden_path("/etc/dirsrv/slapd-*/key*")
        self.add_forbidden_path("/etc/dirsrv/slapd-*/pin.txt")
        self.add_forbidden_path("/etc/dirsrv/slapd-*/pwdfile.txt")

        self.add_forbidden_path("/etc/named.keytab")

        self.add_cmd_output("ls -la /etc/dirsrv/slapd-*/schema/")

        self.add_cmd_output("ipa-getcert list")

        self.add_cmd_output("certutil -L -d /etc/httpd/alias/")
        self.add_cmd_output("certutil -L -d /etc/dirsrv/slapd-*/")

        self.add_cmd_output("klist -ket /etc/dirsrv/ds.keytab")
        self.add_cmd_output("klist -ket /etc/httpd/conf/ipa.keytab")
        self.add_cmd_output("klist -ket /etc/krb5.keytab")

        return

    def postproc(self):
        match = r"(\s*arg \"password )[^\"]*"
        subst = r"\1********"
        self.do_file_sub("/etc/named.conf", match, subst)

