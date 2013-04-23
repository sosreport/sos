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
import os

class Ldap(Plugin):
    """LDAP related information
    """

    plugin_name = "ldap"
    ldap_conf = "/etc/openldap/ldap.conf"

    def get_ldap_opts(self):
        # capture /etc/openldap/ldap.conf options in dict
        # FIXME: possibly not hardcode these options in?
        ldapopts=["URI","BASE","TLS_CACERTDIR"]
        results={}
        tmplist=[]
        for i in ldapopts:
            t=self.do_regex_find_all(r"^(%s)\s+(.*)" % i,self.ldap_conf)
            for x in t:
                results[x[0]]=x[1].rstrip("\n")
        return results

    def setup(self):
        super(Ldap, self).setup()
        self.add_copy_spec("/etc/ldap.conf")

    def postproc(self):
        self.do_file_sub("/etc/ldap.conf", r"(\s*bindpw\s*)\S+", r"\1***")

class RedHatLdap(Ldap, RedHatPlugin):
    """LDAP related information for RedHat based distribution
    """

    packages = ('openldap', 'nss-pam-ldapd')

    def setup(self):
        super(RedHatLdap, self).setup()
        self.add_copy_specs(["/etc/openldap", "/etc/nslcd.conf"])

    def postproc(self):
        self.do_file_sub("/etc/nslcd.conf", r"(\s*bindpw\s*)\S+", r"\1***")

class DebianLdap(Ldap, DebianPlugin, UbuntuPlugin):
    """LDAP related information for Debian based distribution
    """

    ldap_conf = "/etc/ldap/ldap.conf"
    packages = ('slapd', 'ldap-utils')

    def setup(self):
        super(DebianLdap, self).setup()

        ldap_search = "ldapsearch -Q -LLL -Y EXTERNAL -H ldapi:/// "

        self.add_copy_specs(["/etc/ldap/ldap.conf", "/etc/slapd.conf", "/etc/ldap/slapd.d"])

        self.add_cmd_output("ldapsearch -x -b '' -s base 'objectclass=*'")
        self.add_cmd_output(ldap_search + "-b cn=config '(!(objectClass=olcSchemaConfig))'",
            suggest_filename="configuration_minus_schemas")
        self.add_cmd_output(ldap_search + "-b cn=schema,cn=config dn",
            suggest_filename="loaded_schemas")
        self.add_cmd_output(ldap_search + "-b cn=config '(olcAccess=*)' olcAccess olcSuffix",
            suggest_filename="access_control_lists")

    def postproc(self):
        self.do_cmd_output_sub(
        "ldapsearch -Q -LLL -Y EXTERNAL -H ldapi:/// -b cn=config '(!(objectClass=olcSchemaConfig))'",
            r"(olcRootPW\: \s*)\S+", r"\1***")
