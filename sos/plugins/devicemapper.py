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

import os
from sos.plugins import Plugin, RedHatPlugin

class devicemapper(Plugin, RedHatPlugin):
    """device-mapper related information (dm, lvm, multipath)
    """

    optionList = [("lvmdump", 'collect raw metadata from PVs', 'slow', False)]
    optionList = [("lvmdump-a", 'use the -a option of lvmdump (requires the "lvmdump" option)', 'slow', False)]
    dmraidOptions = ['V','b','r','s','tay','rD']

    def do_lvmdump(self):
        """Collects raw metadata directly from the PVs using dd
        """
        cmd = "lvmdump -d '%s'" % os.path.join(self.cInfo['dstroot'],"lvmdump")
        if self.getOption('lvmdump-a'):
          cmd += " -a"
        self.collectExtOutput(cmd)

    def setup(self):
        self.collectExtOutput("/sbin/dmsetup info -c")
        self.collectExtOutput("/sbin/dmsetup table")
        self.collectExtOutput("/sbin/dmsetup status")
        self.collectExtOutput("/sbin/dmsetup ls --tree")

        self.collectExtOutput("/usr/sbin/vgdisplay -vv", root_symlink = "vgdisplay")
        self.collectExtOutput("/usr/sbin/vgscan -vvv")
        self.collectExtOutput("/usr/sbin/pvscan -v")
        self.collectExtOutput("/usr/sbin/lvs -a -o +devices")
        self.collectExtOutput("/usr/sbin/pvs -a -v")
        self.collectExtOutput("/usr/sbin/vgs -v")
        self.collectExtOutput("/sbin/mdadm -D /dev/md*")

        self.addCopySpecs([
            "/etc/lvm",
            "/etc/multipath.conf",
            "/var/lib/multipath/bindings"])
        self.collectExtOutput("/sbin/multipath -v4 -ll")

        self.collectExtOutput("/usr/bin/systool -v -c -b scsi")

        self.collectExtOutput("/bin/ls -lanR /dev")
        self.collectExtOutput("/bin/ls -lanR /sys/block")

        if self.getOption('lvmdump'):
            self.do_lvmdump()

        if os.path.isdir("/sys/block"):
           for disk in os.listdir("/sys/block"):
              if disk in [ ".",  ".." ] or disk.startswith("ram"):
                 continue
              self.collectExtOutput("/usr/bin/udevinfo -ap /sys/block/%s" % (disk))
        for opt in self.dmraidOptions:
            self.collectExtOutput("/sbin/dmraid -%s" % (opt,))
