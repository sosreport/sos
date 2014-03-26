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


from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Kvm(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """KVM related information
    """

    plugin_name = 'kvm'

    def check_enabled(self):
        return os.access("/sys/module/kvm", os.R_OK)

    def setup(self):
        if not os.path.ismount("/sys/kernel/debug"):
            self._debugfs_cleanup = True
            os.popen("mount -t debugfs debugfs /sys/kernel/debug")
        else:
            self._debugfs_cleanup = False
        self.add_copy_spec("/sys/module/kvm/srcversion")
        self.add_copy_spec("/sys/module/kvm_intel/srcversion")
        self.add_copy_spec("/sys/module/kvm_amd/srcversion")
        self.add_copy_spec("/sys/module/ksm/srcversion")
        self.add_cmd_output("kvm_stat --once")

    def postproc(self):
        if self._debugfs_cleanup and os.path.ismount("/sys/kernel/debug"):
            os.popen("umount /sys/kernel/debug")

# vim: et ts=4 sw=4
