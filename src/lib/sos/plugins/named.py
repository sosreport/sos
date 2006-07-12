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
    """This plugin gathers named related information
    """
    def collect(self):
      dnsdir = ""
      self.copyFileOrDir("/etc/named.boot")
      self.copyFileOrDir("/etc/named.conf")
      if os.access("/etc/named.conf", os.R_OK):
        dnsdir = commands.getoutput("/bin/grep -i directory /etc/named.conf | /bin/gawk '{print $2}' | /bin/sed 's/\\\"//g' | /bin/sed 's/\;//g'")
      if os.access("/etc/named.boot", os.R_OK):
        dnsdir = commands.getoutput("/bin/grep -i directory /etc/named.boot | /bin/gawk '{print $2}' | /bin/sed 's/\\\"//g' | /bin/sed 's/\;//g'")
      if '' != dnsdir.strip():
        print "FIX named.py - hangs when named chrooted because of /var/named/chroot/proc"
        #self.copyFileOrDir(dnsdir)
      return

