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

    option_list = [("lvmdump", 'collect raw metadata from PVs', 'slow', False)]
    option_list = [("lvmdump-a", 'use the -a option of lvmdump (requires the "lvmdump" option)', 'slow', False)]
    dmraid_options = ['V','b','r','s','tay','rD']

    def do_lvmdump(self):
        """Collects raw metadata directly from the PVs using dd
        """
        cmd = "lvmdump -d '%s'" % os.path.join(self.commons['dstroot'],"lvmdump")
        if self.get_option('lvmdump-a'):
          cmd += " -a"
        self.add_cmd_output(cmd)

    def setup(self):
        self.add_cmd_output("dmsetup info -c")
        self.add_cmd_output("dmsetup table")
        self.add_cmd_output("dmsetup status")
        self.add_cmd_output("dmsetup ls --tree")

        self.add_cmd_output("vgdisplay -vv", root_symlink = "vgdisplay")
        self.add_cmd_output("vgscan -vvv")
        self.add_cmd_output("pvscan -v")
        self.add_cmd_output("lvs -a -o +devices")
        self.add_cmd_output("pvs -a -v")
        self.add_cmd_output("vgs -v")
        self.add_cmd_output("mdadm -D /dev/md*")

        self.add_copy_specs([
            "/etc/lvm",
            "/etc/multipath/",
            "/etc/multipath.conf",
            "/var/lib/multipath/bindings"])
        self.add_cmd_output("multipath -v4 -ll")

        self.add_cmd_output("systool -v -c -b scsi")

        self.add_cmd_output("ls -lanR /dev")
        self.add_cmd_output("ls -lanR /sys/block")

        if self.get_option('lvmdump'):
            self.do_lvmdump()

        if os.path.isdir("/sys/block"):
           for disk in os.listdir("/sys/block"):
              if disk in [ ".",  ".." ] or disk.startswith("ram"):
                 continue
              self.add_cmd_output("udevinfo -ap /sys/block/%s" % (disk))
        for opt in self.dmraid_options:
            self.add_cmd_output("dmraid -%s" % (opt,))
