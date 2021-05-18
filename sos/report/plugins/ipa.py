# Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, SoSPredicate
from glob import glob


class Ipa(Plugin, RedHatPlugin):

    short_desc = 'Identity, policy, audit'

    plugin_name = 'ipa'
    profiles = ('identity', 'apache')

    ipa_server = False
    ipa_client = False

    files = ('/etc/ipa',)
    packages = ('ipa-server', 'ipa-client', 'freeipa-server', 'freeipa-client')

    def check_ipa_server_version(self):
        if self.is_installed("pki-server") \
                or self.path_exists("/var/lib/pki") \
                or self.path_exists("/usr/share/doc/ipa-server-4.2.0"):
            return "v4"
        elif self.is_installed("pki-common") \
                or self.path_exists("/var/lib/pki-ca/"):
            return "v3"
        return None

    def ca_installed(self):
        # Follow the same checks as IPA CA installer code
        if self.path_exists("%s/conf/ca/CS.cfg" % self.pki_tomcat_dir_v4) \
                or self.path_exists("%s/conf/CS.cfg" % self.pki_tomcat_dir_v3):
            return True

    def ipa_server_installed(self):
        if self.is_installed("ipa-server") \
                or self.is_installed("freeipa-server"):
            return True

    def retrieve_pki_logs(self, ipa_version):
        if ipa_version == "v4":
            self.add_copy_spec([
               "/var/log/pki/pki-tomcat/ca/debug*",
               "/var/log/pki/pki-tomcat/ca/system",
               "/var/log/pki/pki-tomcat/ca/transactions",
               "/var/log/pki/pki-tomcat/ca/selftests.log",
               "/var/log/pki/pki-tomcat/catalina.*",
               "/var/log/pki/pki-ca-spawn.*",
               "/var/log/pki/pki-tomcat/kra/debug*",
               "/var/log/pki/pki-tomcat/kra/system",
               "/var/log/pki/pki-tomcat/kra/transactions",
               "/var/log/pki/pki-kra-spawn.*"
            ])
        elif ipa_version == "v3":
            self.add_copy_spec([
               "/var/log/pki-ca/debug",
               "/var/log/pki-ca/system",
               "/var/log/pki-ca/transactions",
               "/var/log/pki-ca/selftests.log",
               "/var/log/pki-ca/catalina.*",
               "/var/log/pki/pki-ca-spawn.*"
            ])

    def setup(self):
        self.pki_tomcat_dir_v4 = "/var/lib/pki/pki-tomcat"
        self.pki_tomcat_dir_v3 = "/var/lib/pki-ca"

        self.pki_tomcat_conf_dir_v4 = "/etc/pki/pki-tomcat/ca"
        self.pki_tomcat_conf_dir_v3 = "/etc/pki-ca"

        # Returns "v3", "v4", or None
        ipa_version = self.check_ipa_server_version()

        if self.ipa_server_installed():
            self._log_debug("IPA server install detected")

            self._log_debug("IPA version is [%s]" % ipa_version)

            self.add_copy_spec([
                "/var/log/ipaserver-install.log",
                "/var/log/ipaserver-kra-install.log",
                "/var/log/ipareplica-install.log",
                "/var/log/ipareplica-ca-install.log",
                "/var/log/ipa-custodia.audit.log"
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
            "/etc/httpd/alias/*",
            "/etc/named.*",
            "/etc/ipa/ca.crt",
            "/etc/ipa/default.conf",
            "/etc/ipa/kdcproxy/kdcproxy.conf",
            "/etc/ipa/kdcproxy/ipa-kdc-proxy.conf",
            "/etc/ipa/kdcproxy.conf",
            "/root/.ipa/log/cli.log",
            "/var/lib/certmonger/requests/[0-9]*",
            "/var/lib/certmonger/cas/[0-9]*",
            "/var/lib/ipa/ra-agent.pem",
            "/var/lib/ipa/certs/httpd.crt",
            "/var/kerberos/krb5kdc/kdc.crt",
            "/var/lib/ipa/sysrestore/sysrestore.state",
            "/var/log/ipa/healthcheck/healthcheck.log*"
        ])

        #  Make sure to use the right PKI config and NSS DB folders
        if ipa_version == "v4":
            self.pki_tomcat_dir = self.pki_tomcat_dir_v4
            self.pki_tomcat_conf_dir = self.pki_tomcat_conf_dir_v4
        else:
            self.pki_tomcat_dir = self.pki_tomcat_dir_v3
            self.pki_tomcat_conf_dir = self.pki_tomcat_conf_dir_v3

        self.add_cmd_output("certutil -L -d %s/alias" % self.pki_tomcat_dir)
        self.add_copy_spec("%s/CS.cfg" % self.pki_tomcat_conf_dir)

        self.add_forbidden_path([
            "/etc/pki/nssdb/key*",
            "/etc/dirsrv/slapd-*/key*",
            "/etc/dirsrv/slapd-*/pin.txt",
            "/etc/dirsrv/slapd-*/pwdfile.txt",
            "/etc/httpd/alias/ipasession.key",
            "/etc/httpd/alias/key*",
            "/etc/httpd/alias/pin.txt",
            "/etc/httpd/alias/pwdfile.txt",
            "/etc/named.keytab",
            "%s/alias/key*" % self.pki_tomcat_dir,
            "%s/flatfile.txt" % self.pki_tomcat_conf_dir,
            "%s/password.conf" % self.pki_tomcat_conf_dir,
        ])

        self.add_cmd_output([
            "ls -la /etc/dirsrv/slapd-*/schema/",
            "certutil -L -d /etc/httpd/alias/",
            "pki-server cert-find --show-all",
            "pki-server subsystem-cert-validate ca",
            "klist -ket /etc/dirsrv/ds.keytab",
            "klist -ket /etc/httpd/conf/ipa.keytab",
            "klist -ket /var/lib/ipa/gssproxy/http.keytab"
        ])

        getcert_pred = SoSPredicate(self,
                                    services=['certmonger'])

        self.add_cmd_output("getcert list", pred=getcert_pred)

        for certdb_directory in glob("/etc/dirsrv/slapd-*/"):
            self.add_cmd_output("certutil -L -d %s" % certdb_directory)
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
