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
import commands
import os

class named(sos.plugintools.PluginBase):
    """named related information
    """
    def checkenabled(self):
       if self.cInfo["policy"].pkgByName("bind") or os.path.exists("/etc/named.conf") or os.path.exists("/etc/sysconfig/named"):
          return True
       return False

    def setup(self):
       dnsdir = ""
       self.addCopySpec("/etc/named.boot")
       self.addCopySpec("/etc/named.conf")
       self.addCopySpec("/etc/sysconfig/named")
       if os.access("/etc/named.conf", os.R_OK):
          dnsdir = commands.getoutput("/bin/grep -i directory /etc/named.conf | /bin/gawk '{print $2}' | /bin/sed 's/\\\"//g' | /bin/sed 's/\;//g'")
       if os.access("/etc/named.boot", os.R_OK):
          dnsdir = commands.getoutput("/bin/grep -i directory /etc/named.boot | /bin/gawk '{print $2}' | /bin/sed 's/\\\"//g' | /bin/sed 's/\;//g'")
       if '' != dnsdir.strip():
          self.addCopySpec(dnsdir)
          self.addForbiddenPath('/var/named/chroot/proc')
          self.addForbiddenPath('/var/named/chroot/dev')
       return
