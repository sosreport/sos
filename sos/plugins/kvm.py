# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


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
