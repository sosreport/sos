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

class devicemapper(sos.plugintools.PluginBase):
    """device-mapper related information (dm, lvm, multipath)
    """

    optionList = [("lvmdump", 'collect an lvmdump', 'fast', False),
                  ("lvmdump-am", 'attempt to collect an lvmdump with advanced ' \
                    + 'options and raw metadata collection', 'slow', False),]

    dmraidOptions = ['V','b','r','s','tay','rD']

    def do_lvmdump(self, metadata=False):
        """Calls the LVM2 lvmdump script to collect detailed diagnostic information
        """
        lvmdump_cmd = "lvmdump %s -d '%s'" 
        lvmdump_opts = ""
        if metadata:
            lvmdump_opts = "-a -m"
        cmd = lvmdump_cmd % (lvmdump_opts,
                             os.path.join(self.cInfo['cmddir'],
                             "devicemapper","lvmdump"))
        self.callExtProg(cmd)

    def setup(self):
        self.collectExtOutput("/sbin/dmsetup info -c")
        self.collectExtOutput("/sbin/dmsetup table")
        self.collectExtOutput("/sbin/dmsetup status")
        self.collectExtOutput("/sbin/dmsetup ls --tree")

        # use locking_type 0 (no locks) when running LVM2 commands, from lvm.conf:
        # Turn locking off by setting to 0 (dangerous: risks metadata corruption
        # if LVM2 commands get run concurrently).
        # None of the commands issued by sos ever modify metadata and this avoids
        # the possibility of hanging lvm commands when another process or node
        # holds a conflicting lock.
        lvm_opts = '--config="global{locking_type=0}"'
        
        self.collectExtOutput(
            "/sbin/vgdisplay -vv %s" % lvm_opts, suggest_filename='vgdisplay_-vv',
            symlink = "vgdisplay"
        )
        self.collectExtOutput("/sbin/vgscan -vvv %s" % lvm_opts, suggest_filename='vgscan_-vvv')
        self.collectExtOutput("/sbin/pvscan -v %s" % lvm_opts, suggest_filename='pvscan_-v')
        self.collectExtOutput("/sbin/lvs -a -o +devices %s" % lvm_opts, suggest_filename='lvs_-a_-o_+devices')
        self.collectExtOutput("/sbin/pvs -a -v %s" % lvm_opts, suggest_filename='pvs_-a_-v')
        self.collectExtOutput("/sbin/vgs -v %s" % lvm_opts, suggest_filename='vgs_-v')
        self.collectExtOutput("/sbin/mdadm -D /dev/md*")

        self.addCopySpec("/etc/lvm")

        self.addCopySpec("/etc/multipath.conf")
        self.addCopySpec("/etc/multipath/")
        self.addCopySpec("/var/lib/multipath/bindings")
        self.collectExtOutput("/sbin/multipath -v4 -ll")

        self.collectExtOutput("/usr/bin/systool -v -b scsi")
        self.collectExtOutput("/usr/bin/systool -v -c scsi_device")
        self.collectExtOutput("/usr/bin/systool -v -c scsi_host")
        self.collectExtOutput("/usr/bin/systool -v -c scsi_disk")
        self.collectExtOutput("/usr/bin/systool -v -c scsi_generic")
        self.collectExtOutput("/usr/bin/systool -v -m scsi_mod")
        self.collectExtOutput("/usr/bin/systool -v -m scsi_transport_fc")

        self.collectExtOutput("/bin/ls -laR /dev")
        self.collectExtOutput("/bin/ls -laR /sys/block")

        if self.getOption('lvmdump'):
            self.do_lvmdump()
        elif self.getOption('lvmdump-am'):
            self.do_lvmdump(metadata=True)

        if os.path.isdir("/sys/block"):
           for disk in os.listdir("/sys/block"):
              if disk in [ ".",  ".." ] or disk.startswith("ram"):
                 continue
              self.collectExtOutput("/sbin/udevadm info -ap /sys/block/%s" % (disk))
        for opt in self.dmraidOptions:
            self.collectExtOutput("/sbin/dmraid -%s" % (opt,))

        return
