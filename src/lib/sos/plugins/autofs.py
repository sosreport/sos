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
        if self.cInfo["policy"].runlevelDefault() in self.cInfo["policy"].runlevelByService("autofs"):
            return True
        return False
    
    def checkdebug(self):
        """ testing if autofs debug has been enabled anywhere
        """
        # Global debugging
        f=open('/etc/sysconfig/autofs','r')
        content=f.read()
        f.close()
        reg=re.compile(r"^(DEFAULT_LOGGING|DAEMONOPTIONS)=(.*)\D",re.MULTILINE)
        optlist=[]
        for opt in reg.findall(content):
            for opt2 in opt.split(" "):
                optlist.append(opt2)
        for dtest in optlist:
            if dtest == "--debug" or dtest == "debug":
                return True
    
    def getdaemondebug(self):
        """ capture daemon debug output
        """
        f=open('/etc/sysconfig/autofs','r')
        content=f.read()
        f.close()
        reg=re.compile(r"^(daemon.*)\s+(\/var\/log\/.*)\D",re.MULTILINE)
        for i in reg.findall(content):
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
        if self.checkdebug() is True:
            self.addCopySpec(self.getdaemondebug())
        return

