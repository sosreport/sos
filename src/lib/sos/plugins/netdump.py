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

#############################################################
# This plugin assumes is to assist in troubleshooting netdump
# issues that deal with netdump configuration.  Any improvements
# to the plugin are appreciated.  Please send them to
# sos@lists.fedorahosted.org
# thanks
#############################################################
# grabs both client and server netdump configs

import sos.plugintools
from os import exists

class netdump(sos.plugintools.PluginBase):
    """Netdump Configuration Information
    """

    def checkenabled(self):
        if self.cInfo["policy"].pkgByName("netdump") or exists("/etc/sysconfig/netdump*"):
            return True
        return False

    def setup(self):
        self.addCopySpec("/etc/sysconfig/netdump")
        return
