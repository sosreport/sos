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
    def collect(self):
        self.copyFileOrDir("/proc/filesystems")
        self.copyFileOrDir("/etc/fstab")
        self.copyFileOrDir("/proc/mounts")
        self.copyFileOrDir("/proc/mdstat")
        self.copyFileOrDir("/etc/raidtab")
        self.copyFileOrDir("/etc/mdadm.conf")
        self.copyFileOrDir("/etc/auto.master")
        self.copyFileOrDir("/etc/auto.misc")
        self.copyFileOrDir("/etc/auto.net")
        
        self.runExe("/bin/df -al")
        self.runExe("/usr/sbin/lsof -b +M -n -l")
        self.runExe("/bin/mount -l")
        self.runExe("/sbin/blkid")

        raiddevs = commands.getoutput("/bin/cat /proc/partitions | /bin/egrep -v \"^major|^$\" | /bin/awk '{print $4}' | /bin/grep \/ | /bin/egrep -v \"p[0123456789]$\"")
        disks = commands.getoutput("/bin/cat /proc/partitions | /bin/egrep -v \"^major|^$\" | /bin/awk '{print $4}' | /bin/grep -v / | /bin/egrep -v \"[0123456789]$\"")
        for disk in raiddevs.split('\n'):
          if '' != disk.strip():
            self.runExe("/sbin/fdisk -l /dev/%s 2>&1" % (disk,))
        for disk in disks.split('\n'):
          if '' != disk.strip():
            self.runExe("/sbin/fdisk -l /dev/%s 2>&1" % (disk,))
        return

