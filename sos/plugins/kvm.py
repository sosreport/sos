# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class Kvm(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Kernel virtual machine
    """

    plugin_name = 'kvm'
    profiles = ('system', 'virt')
    debugfs_path = "/sys/kernel/debug"

    _debugfs_cleanup = False

    def check_enabled(self):
        return os.access("/sys/module/kvm", os.R_OK)

    def setup(self):
        self.add_copy_spec([
            "/sys/module/kvm/srcversion",
            "/sys/module/kvm_intel/srcversion",
            "/sys/module/kvm_amd/srcversion",
            "/sys/module/ksm/srcversion"
        ])
        if not os.path.ismount(self.debugfs_path):
            self._debugfs_cleanup = True
            r = self.call_ext_prog("mount -t debugfs debugfs %s"
                                   % self.debugfs_path)
            if r['status'] != 0:
                self._log_error("debugfs not mounted and mount attempt failed")
                self._debugfs_cleanup = False
                return
        self.add_cmd_output("kvm_stat --once")

    def postproc(self):
        if self._debugfs_cleanup and os.path.ismount(self.debugfs_path):
            self.call_ext_prog("umount %s" % self.debugfs_path)
            self._log_error("could not unmount %s" % self.debugfs_path)

# vim: set et ts=4 sw=4 :
