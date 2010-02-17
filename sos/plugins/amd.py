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

class amd(sos.plugintools.PluginBase):
    """Amd automounter information
    """
    def checkenabled(self):
       if self.isInstalled("am-utils") or os.path.exists("/etc/rc.d/init.d/amd"):
          return True
       return False

    def setup(self):
        self.addCopySpec("/etc/amd.*")
        self.addCopySpec("/etc/rc.d/init.d/amd")
        self.addCopySpec("/etc/sysconfig/amd")
        self.collectExtOutput("/bin/rpm -qV am-utils")
        self.collectExtOutput("/bin/egrep -e 'automount|pid.*nfs' /proc/mounts")
        self.collectExtOutput("/bin/mount | egrep -e 'automount|pid.*nfs'")
        return

