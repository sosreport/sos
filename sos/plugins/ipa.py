# Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin
from glob import glob
from os.path import exists


class Ipa(Plugin, RedHatPlugin):
    """ Identity, policy, audit
    """

    plugin_name = 'ipa'
    profiles = ('identity',)

    ipa_server = False
    ipa_client = False

    files = ('/etc/ipa',)
    packages = ('ipa-server', 'ipa-client', 'freeipa-server', 'freeipa-client')

    def check_ipa_server_version(self):
        if self.is_installed("pki-server") \
                or exists("/var/lib/pki") \
                or exists("/usr/share/doc/ipa-server-4.2.0"):
            return "v4"
        elif self.is_installed("pki-common") \
                or exists("/var/lib/pki-ca/"):
            return "v3"

    def ca_installed(self):
        # Follow the same checks as IPA CA installer code
        if exists("%s/conf/ca/CS.cfg" % self.pki_tomcat_dir_v4) \
                or exists("%s/conf/CS.cfg" % self.pki_tomcat_dir_v3):
            return True

    def ipa_server_installed(self):
        if self.is_installed("ipa-server") \
                or self.is_installed("freeipa-server"):
            return True

    def retrieve_pki_logs(self, ipa_version):
        if ipa_version == "v4":
            self.add_copy_spec([
               "/var/log/pki/pki-tomcat/ca/debug",
               "/var/log/pki/pki-tomcat/ca/system",
               "/var/log/pki/pki-tomcat/ca/transactions",
               "/var/log/pki/pki-tomcat/catalina.*",
               "/var/log/pki/pki-ca-spawn.*"
            ])
        elif ipa_version == "v3":
            self.add_copy_spec([
               "/var/log/pki-ca/debug",
               "/var/log/pki-ca/system",
               "/var/log/pki-ca/transactions",
               "/var/log/pki-ca/catalina.*",
               "/var/log/pki/pki-ca-spawn.*"
            ])

    def check_enabled(self):
        self.ipa_server = self.is_installed("ipa-server")
        self.ipa_client = self.is_installed("ipa-client")
        return Plugin.check_enabled(self)

    def setup(self):
        self.pki_tomcat_dir_v4 = "/var/lib/pki/pki-tomcat"
        self.pki_tomcat_dir_v3 = "/var/lib/pki-ca"

        if self.ipa_server_installed():
            self._log_debug("IPA server install detected")

            ipa_version = self.check_ipa_server_version()
            self._log_debug("IPA version is [%s]" % ipa_version)

            self.add_copy_spec([
                "/var/log/ipaserver-install.log",
                "/var/log/ipareplica-install.log"
            ])

        if self.ca_installed():
            self._log_debug("CA is installed: retrieving PKI logs")
            self.retrieve_pki_logs(ipa_version)

        self.add_copy_spec([
            "/var/log/ipaclient-install.log",
            "/var/log/ipaupgrade.log",
            "/var/log/krb5kdc.log",
            "/var/log/dirsrv/slapd-*/logs/access",
            "/var/log/dirsrv/slapd-*/logs/errors",
            "/etc/dirsrv/slapd-*/dse.ldif",
            "/etc/dirsrv/slapd-*/schema/99user.ldif",
            "/etc/hosts",
            "/etc/named.*",
            "/etc/pki-ca/CS.cfg",
            "/etc/ipa/ca.crt",
            "/etc/ipa/default.conf",
            "/var/lib/certmonger/requests/[0-9]*",
            "/var/lib/certmonger/cas/[0-9]*"
        ])

        self.add_forbidden_path("/etc/pki/nssdb/key*")
        self.add_forbidden_path("/etc/pki-ca/flatfile.txt")
        self.add_forbidden_path("/etc/pki-ca/password.conf")
        self.add_forbidden_path("/var/lib/pki-ca/alias/key*")
        self.add_forbidden_path("/etc/dirsrv/slapd-*/key*")
        self.add_forbidden_path("/etc/dirsrv/slapd-*/pin.txt")
        self.add_forbidden_path("/etc/dirsrv/slapd-*/pwdfile.txt")
        self.add_forbidden_path("/etc/named.keytab")

        self.add_cmd_output([
            "ls -la /etc/dirsrv/slapd-*/schema/",
            "getcert list",
            "certutil -L -d /var/lib/pki-ca/alias",
            "certutil -L -d /etc/httpd/alias/",
            "klist -ket /etc/dirsrv/ds.keytab",
            "klist -ket /etc/httpd/conf/ipa.keytab"
        ])
        for certdb_directory in glob("/etc/dirsrv/slapd-*/"):
            self.add_cmd_output(["certutil -L -d %s" % certdb_directory])
        return

    def postproc(self):
        match = r"(\s*arg \"password )[^\"]*"
        subst = r"\1********"
        self.do_file_sub("/etc/named.conf", match, subst)

        self.do_cmd_output_sub("getcert list",
                               r"(pin=)'(\d+)'",
                               r"\1'***'")

        request_logs = "/var/lib/certmonger/requests/[0-9]*"
        for request_log in glob(request_logs):
            self.do_file_sub(request_log,
                             r"(key_pin=)(\d+)",
                             r"\1***")


# vim: set et ts=4 sw=4 :
