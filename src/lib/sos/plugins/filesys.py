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

class filesys(sos.plugintools.PluginBase):
    """This plugin gathers infomraiton on filesystems
    """
    def setup(self):
        self.addCopySpec("/proc/filesystems")
        self.addCopySpec("/etc/fstab")
        self.addCopySpec("/proc/mounts")
        self.addCopySpec("/proc/mdstat")
        self.addCopySpec("/etc/raidtab")
        self.addCopySpec("/etc/mdadm.conf")
        self.addCopySpec("/etc/auto.master")
        self.addCopySpec("/etc/auto.misc")
        self.addCopySpec("/etc/auto.net")
        
        self.collectExtOutput("/bin/df -al", root_symlink = "df")
        self.collectExtOutput("/usr/sbin/lsof -b +M -n -l", root_symlink = "lsof")
        self.collectExtOutput("/bin/mount -l", root_symlink = "mount")
        self.collectExtOutput("/sbin/blkid")

        raiddevs = commands.getoutput("/bin/cat /proc/partitions | /bin/egrep -v \"^major|^$\" | /bin/awk '{print $4}' | /bin/grep \/ | /bin/egrep -v \"p[0123456789]$\"")
        disks = commands.getoutput("/bin/cat /proc/partitions | /bin/egrep -v \"^major|^$\" | /bin/awk '{print $4}' | /bin/grep -v / | /bin/egrep -v \"[0123456789]$\"")
        for disk in raiddevs.split('\n'):
          if '' != disk.strip():
            self.collectExtOutput("/sbin/fdisk -l /dev/%s 2>&1" % (disk,))
        for disk in disks.split('\n'):
          if '' != disk.strip():
            self.collectExtOutput("/sbin/fdisk -l /dev/%s 2>&1" % (disk,))
        return

