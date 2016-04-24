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
        self.add_forbidden_path("/etc/openldap/certs/password")
        self.add_forbidden_path("/etc/openldap/certs/pwfile.txt")
        self.add_forbidden_path("/etc/openldap/certs/pin.txt")
        self.add_forbidden_path("/etc/openldap/certs/*passw*")
        self.add_forbidden_path("/etc/openldap/certs/key3.db")
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
        self.do_cmd_output_sub(
            "ldapsearch",
            r"(olcRootPW\: \s*)\S+",
            r"\1********"
        )

# vim: set et ts=4 sw=4 :
