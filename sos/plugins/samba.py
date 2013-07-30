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

class Samba(Plugin):
    """Samba related information
    """
    plugin_name = "samba"

    def setup(self):
        self.add_copy_specs([
            "/etc/samba",
            "/var/log/samba/*",])
        self.add_cmd_output("wbinfo --domain='.' -g")
        self.add_cmd_output("wbinfo --domain='.' -u")
        self.add_cmd_output("testparm -s -v")


class RedHatSamba(Samba, RedHatPlugin):
    """Samba related information for RedHat based distributions
    """
    def setup(self):
        super(RedHatSamba, self).setup()
        # FIXME: krb5 specific
        self.add_copy_specs([
            "/etc/krb5.conf",
            "/etc/krb5.keytab"])

class DebianSamba(Samba, DebianPlugin, UbuntuPlugin):
    """Samba related information for Debian based distributions
    """
    def setup(self):
        super(DebianSamba, self).setup()
