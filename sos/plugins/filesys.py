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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin
import os
import re
from itertools import *

class filesys(Plugin, RedHatPlugin, UbuntuPlugin):
    """information on filesystems
    """
    option_list = [("lsof", 'gathers information on all open files', 'slow', False)]
    option_list = [("dumpe2fs", 'dump filesystem information', 'slow', False)]

    def setup(self):
        self.add_copy_specs([
            "/proc/filesystems",
            "/etc/fstab",
            "/proc/self/mounts",
            "/proc/mounts",
            "/proc/mdstat",
            "/etc/raidtab",
            "/etc/mdadm.conf"])
        mounts = self.get_cmd_output_now("/bin/mount -l", root_symlink = "mount")

        self.add_cmd_output("/bin/findmnt")
        self.add_cmd_output("/bin/df -al", root_symlink = "df")
        self.add_cmd_output("/bin/df -ali")
        if self.get_option('lsof'):
            self.add_cmd_output("/usr/sbin/lsof -b +M -n -l -P", root_symlink = "lsof")
        self.add_cmd_output("/sbin/blkid -c /dev/null")
        self.add_cmd_output("/usr/bin/lsblk")

        part_titlep = re.compile("^major")
        blankp = re.compile("^$")
        partlist = []
        devlist = []
        try:
            for line in open('/proc/partitions'):
                if((bool(part_titlep.match(line))) | (bool(blankp.match(line)))):
                    continue
                partlist.append('/dev/' + line.split()[-1])
        except IOError:
            exit(1)
        if os.path.exists("/sbin/hdparm"):
            for dev in partlist:
                ret, hdparm, time = self.call_ext_prog('/sbin/hdparm -g %s' %(dev))
                if(ret == 0):
                    start_geo = hdparm.strip().split("\n")[-1].strip().split()[-1]
                    if(start_geo == "0"):
      	                devlist.append(dev)
        else:
            # Cheaper heuristic as RHEL* does not ship hdparm for S390(x)
            # Skips least dm-.* correctly
            part_in_disk = re.compile("^/dev/[a-z]+$")
            for dev in partlist:
                if bool(part_in_disk.match(dev)):
                    devlist.append(dev)

        for i in devlist:
            self.add_cmd_output("/sbin/parted -s %s print" % (i))

        if self.get_option('dumpe2fs'):
            for extfs in izip(self.do_regex_find_all(r"^(/dev/.+) on .+ type ext.\s+", mounts)):
                self.add_cmd_output("/sbin/dumpe2fs %s" % (extfs))
