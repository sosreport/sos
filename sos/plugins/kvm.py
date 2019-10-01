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

    def check_enabled(self):
        return os.access("/sys/module/kvm", os.R_OK)

    def setup(self):
        self.add_copy_spec([
            "/sys/module/kvm/srcversion",
            "/sys/module/kvm_intel/srcversion",
            "/sys/module/kvm_amd/srcversion",
            "/sys/module/ksm/srcversion"
        ])

        self.add_cmd_output("kvm_stat --once")

# vim: set et ts=4 sw=4 :
