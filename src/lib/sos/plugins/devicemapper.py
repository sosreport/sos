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
from sos.helpers import sosGetCommandOutput

class devicemapper(sos.plugintools.PluginBase):
    """device-mapper related information (dm, lvm, multipath)
    """

    optionList = [("lvmdump", 'collect raw metadata from PVs', 'slow', False)]

    def setup(self):
        self.collectExtOutput("/sbin/dmsetup info -c")
        self.collectExtOutput("/sbin/dmsetup table")
        self.collectExtOutput("/sbin/dmsetup status")

        self.collectExtOutput("/usr/sbin/vgdisplay -vv", root_symlink = "vgdisplay")
        self.collectExtOutput("/usr/sbin/vgscan -vvv")
        self.collectExtOutput("/usr/sbin/pvscan -v")
        self.collectExtOutput("/usr/sbin/lvs -a -o +devices")
        self.collectExtOutput("/usr/sbin/pvs -a -v")
        self.collectExtOutput("/usr/sbin/vgs -v")

        self.addCopySpec("/etc/lvm/lvm.conf")

        self.addCopySpec("/etc/multipath.conf")
        self.addCopySpec("/var/lib/multipath/bindings")
        self.collectExtOutput("/sbin/multipath -v4 -ll")

        self.collectExtOutput("/usr/bin/systool -v -C -b scsi")

        self.collectExtOutput("/bin/ls -laR /dev")
        self.collectExtOutput("/bin/ls -laR /sys/block")

        if self.getOption('lvmdump'):
           sosGetCommandOutput("lvmdump -d %s" % os.path.join(self.cInfo['dstroot'],"lvmdump"))

        if os.path.isdir("/sys/block"):
           for disk in os.listdir("/sys/block"):
              if disk in [ ".",  ".." ] or disk.startswith("ram"):
                 continue
              self.collectExtOutput("/usr/bin/udevinfo -ap /sys/block/%s" % (disk))

        return
