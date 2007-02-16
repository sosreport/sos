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

import sos.plugintools

class ldap(sos.plugintools.PluginBase):
    """This plugin gathers LDAP related information
    """
    def setup(self):
        self.addCopySpec("/etc/ldap.conf")
        self.addCopySpec("/etc/openldap")
        return

    def postproc(self):
        self.doRegexSub("/etc/ldap.conf", r"(\s*bindpw\s*)\S+", r"\1***")
        return
