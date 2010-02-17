## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>

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

class kvm(sos.plugintools.PluginBase):
    """KVM related information
    """

    optionList = [("topOutput", '5x iterations of top data', 'slow', False)]

    def checkenabled(self):
        if os.access("/sys/module/kvm", os.R_OK):
            return True
        return False

    def setup(self):
        if not os.path.ismount("/sys/kernel/debug"):
            self._debugfs_cleanup = True
            os.popen("mount -t debugfs debugfs /sys/kernel/debug")
        else:
            self._debugfs_cleanup = False
        self.addCopySpec("/sys/module/kvm/srcversion")
        self.addCopySpec("/sys/module/kvm_intel/srcversion")
        self.addCopySpec("/sys/module/kvm_amd/srcversion")
        self.addCopySpec("/sys/module/ksm/srcversion")
        if self.getOption('topOutput'):
            self.collectExtOutput("/usr/bin/top -b -d 1 -n 5")
        self.collectExtOutput("/usr/bin/kvm_stat --once")
        return

    def postproc(self):
        if self._debugfs_cleanup and os.path.ismount("/sys/kernel/debug"):
            os.popen("umount /sys/kernel/debug")
        return

