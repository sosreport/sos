## Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

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
import os
from stat import ST_SIZE

class nfsserver(sos.plugintools.PluginBase):
    """NFS server-related information
    """
    def checkenabled(self):
       if self.policy().runlevelDefault() in self.policy().runlevelByService("nfs"):
          return True

       try:
          if os.stat("/etc/exports")[ST_SIZE] > 0 or os.stat("/var/lib/nfs/xtab")[ST_SIZE] > 0:
             return True
       except:
          pass

       return False

    def setup(self):
        self.addCopySpec("/etc/exports")
        self.addCopySpec("/var/lib/nfs/etab")
        self.addCopySpec("/var/lib/nfs/xtab")
        self.addCopySpec("/var/lib/nfs/rmtab")
        self.collectExtOutput("/usr/sbin/rpcinfo -p localhost")
        self.collectExtOutput("/usr/sbin/nfsstat -a")
        return

