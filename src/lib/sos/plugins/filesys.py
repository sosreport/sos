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
from sos.helpers import sosReadFile
import os

class filesys(sos.plugintools.PluginBase):
    """information on filesystems
    """
    def setup(self):
        self.addCopySpec("/proc/filesystems")
        self.addCopySpec("/etc/fstab")
        self.addCopySpec("/proc/self/mounts")
        self.addCopySpec("/proc/mounts")
        self.addCopySpec("/proc/mdstat")
        self.addCopySpec("/etc/raidtab")
        mounts = self.collectOutputNow("/bin/mount -l", root_symlink = "mount")
        self.addCopySpec("/etc/mdadm.conf")
        
        self.collectExtOutput("/bin/df -al", root_symlink = "df")
        self.collectExtOutput("/sbin/blkid")

        for disk in os.listdir("/sys/block"):
            if disk in [ ".",  ".." ] or disk.startswith("ram") or sosReadFile("/sys/block/%s/removable" % disk ).strip() == "1":
                continue
            self.collectExtOutput("/sbin/fdisk -l /dev/%s" % (disk))

        for extfs in self.doRegexFindAll(r"^(/dev/.+) on .+ type ext.\s+", mounts):
            self.collectExtOutput("/sbin/tune2fs -l %s" % (extfs))

        return
