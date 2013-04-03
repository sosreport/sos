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

    def setup(self):
        super(ldap, self).setup()

class RedHatLdap(Ldap, RedHatPlugin):
    """LDAP related information for RedHat based distribution
    """

    files = ('/etc/openldap/ldap.conf',)
    packages = ('openldap', 'nss-pam-ldapd')

    def setup(self):
        super(RedHatLdap, self).setup()

    def get_ldap_opts(self):
        # capture /etc/openldap/ldap.conf options in dict
        # FIXME: possibly not hardcode these options in?
        ldapopts=["URI","BASE","TLS_CACERTDIR"]
        results={}
        tmplist=[]
        for i in ldapopts:
            t=self.do_regex_find_all(r"^(%s)\s+(.*)" % i,"/etc/openldap/ldap.conf")
            for x in t:
                results[x[0]]=x[1].rstrip("\n")
        return results

    def setup(self):
        self.add_copy_specs(["/etc/ldap.conf", "/etc/openldap", "/etc/nslcd.conf"])

    def postproc(self):
        self.do_file_sub("/etc/ldap.conf", r"(\s*bindpw\s*)\S+", r"\1***")
        self.do_file_sub("/etc/nslcd.conf", r"(\s*bindpw\s*)\S+", r"\1***")

class DebianLdap(Ldap, DebianPlugin, UbuntuPlugin):
    """LDAP related information for Debian based distribution
    """

    def setup(self):
        super(DebianLdap, self).setup()

    files = ('/etc/ldap/ldap.conf',)
    packages = ('slapd', 'ldap-utils')

    def get_ldap_opts(self):
        # capture /etc/ldap/ldap.conf options in dict
        # FIXME: possibly not hardcode these options in?
        ldapopts=["URI","BASE","TLS_CACERTDIR"]
        results={}
        tmplist=[]
        for i in ldapopts:
            t=self.do_regex_find_all(r"^(%s)\s+(.*)" % i,"/etc/ldap/ldap.conf")
            for x in t:
                results[x[0]]=x[1].rstrip("\n")
        return results

    def setup(self):
        self.add_copy_specs(["/etc/ldap/ldap.conf", "/etc/ldap/slapd.d"])

    def postproc(self):
        self.do_file_sub("/etc/ldap/ldap.conf", r"(\s*bindpw\s*)\S+", r"\1***")
