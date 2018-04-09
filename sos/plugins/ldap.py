# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Ldap(Plugin):
    """LDAP configuration
    """

    plugin_name = "ldap"
    profiles = ('identity', 'sysmgmt', 'system')
    ldap_conf = "/etc/openldap/ldap.conf"

    def setup(self):
        super(Ldap, self).setup()
        self.add_copy_spec("/etc/ldap.conf")

    def postproc(self):
        self.do_file_sub("/etc/ldap.conf", r"(\s*bindpw\s*)\S+", r"\1******")


class RedHatLdap(Ldap, RedHatPlugin):

    packages = ('openldap', 'nss-pam-ldapd')
    files = ('/etc/ldap.conf', '/etc/pam_ldap.conf')

    def setup(self):
        super(RedHatLdap, self).setup()
        self.add_forbidden_path([
            "/etc/openldap/certs/password",
            "/etc/openldap/certs/pwfile.txt",
            "/etc/openldap/certs/pin.txt",
            "/etc/openldap/certs/*passw*",
            "/etc/openldap/certs/key3.db"
        ])

        self.add_copy_spec([
            self.ldap_conf,
            "/etc/openldap/certs/cert8.db",
            "/etc/openldap/certs/secmod.db",
            "/etc/nslcd.conf",
            "/etc/pam_ldap.conf"
        ])
        self.add_cmd_output("certutil -L -d /etc/openldap")

    def postproc(self):
        super(RedHatLdap, self).postproc()
        self.do_file_sub(
            "/etc/nslcd.conf",
            r"(\s*bindpw\s*)\S+",
            r"\1********"
        )
        self.do_file_sub(
            "/etc/pam_ldap.conf",
            r"(\s*bindpw\s*)\S+",
            r"\1********"
        )


class DebianLdap(Ldap, DebianPlugin, UbuntuPlugin):

    ldap_conf = "/etc/ldap/ldap.conf"
    packages = ('slapd', 'ldap-utils')

    def setup(self):
        super(DebianLdap, self).setup()

        ldap_search = "ldapsearch -Q -LLL -Y EXTERNAL -H ldapi:/// "

        self.add_copy_spec([
            self.ldap_conf,
            "/etc/slapd.conf",
            "/etc/ldap/slapd.d"
            "/etc/nslcd.conf",
        ])

        self.add_cmd_output("ldapsearch -x -b '' -s base 'objectclass=*'")
        self.add_cmd_output(
            ldap_search + "-b cn=config '(!(objectClass=olcSchemaConfig))'",
            suggest_filename="configuration_minus_schemas")
        self.add_cmd_output(
            ldap_search + "-b cn=schema,cn=config dn",
            suggest_filename="loaded_schemas")
        self.add_cmd_output(
            ldap_search + "-b cn=config '(olcAccess=*)' olcAccess olcSuffix",
            suggest_filename="access_control_lists")

    def postproc(self):
        super(DebianLdap, self).postproc()
        self.do_file_sub(
            "/etc/nslcd.conf",
            r"(\s*bindpw\s*)\S+",
            r"\1********"
        )
        self.do_cmd_output_sub(
            "ldapsearch",
            r"(olcRootPW\: \s*)\S+",
            r"\1********"
        )


# vim: set et ts=4 sw=4 :
