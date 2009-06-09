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
    # ntp and dirserver stuff are covered in existing sos plugins, so we really only
    # need to get kerberos and ipa specific addons.

    def checkenabled(self):
       if self.isInstalled("ipa-server") or os.path.exists("/etc/ipa"):
          return True
       return False

    def setup(self):
        self.addCopySpec("/etc/dirsrv/ds.keytab")
        self.addCopySpec("/etc/ipa/ipa.conf")
        self.addCopySpec("/etc/krb5.conf")
        self.addCopySpec("/etc/krb5.keytab")
        return

