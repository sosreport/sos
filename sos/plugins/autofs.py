## Copyright (C) 2007 Red Hat, Inc., Adam Stokes <astokes@redhat.com>

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
import os, re

class autofs(sos.plugintools.PluginBase):
    """autofs server-related information
    """
    def checkenabled(self):
        self.packages = [ "autofs" ]
        self.files = [ "/etc/sysconfig/autofs" ]
        return sos.plugintools.PluginBase.checkenabled(self)
    
    def checkdebug(self):
        """ testing if autofs debug has been enabled anywhere
        """
        # Global debugging
        optlist=[]
        opt = self.fileGrep(r"^(DEFAULT_LOGGING|DAEMONOPTIONS)=(.*)", "/etc/sysconfig/autofs")
        for opt1 in opt:
            for opt2 in opt1.split(" "):
                optlist.append(opt2)
        for dtest in optlist:
            if dtest == "--debug" or dtest == "debug":
                return True
    
    def getdaemondebug(self):
        """ capture daemon debug output
        """
        debugout = self.fileGrep(r"^(daemon.*)\s+(\/var\/log\/.*)", "/etc/sysconfig/autofs")
        for i in debugout:
            return i[1]
    
    def setup(self):
        self.addCopySpec("/etc/auto*")
        self.addCopySpec("/etc/sysconfig/autofs")
        self.addCopySpec("/etc/init.d/autofs")
        self.collectExtOutput("/bin/rpm -qV autofs")
        self.collectExtOutput("/etc/init.d/autofs status")
        self.collectExtOutput("ps auxwww | grep automount")
        self.collectExtOutput("/bin/egrep -e 'automount|pid.*nfs' /proc/mounts")
        self.collectExtOutput("/bin/mount | egrep -e 'automount|pid.*nfs'")
        self.collectExtOutput("/sbin/chkconfig --list autofs")
        if self.checkdebug():
            self.addCopySpec(self.getdaemondebug())
        return

