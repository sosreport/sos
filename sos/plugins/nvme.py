# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class Nvme(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Collect config and system information about NVMe devices"""

    plugin_name = "nvme"
    packages = ('nvme-cli',)

    def get_nvme_devices(self):
        sys_block = os.listdir('/sys/block/')
        return [dev for dev in sys_block if dev.startswith('nvme')]

    def setup(self):
        self.add_cmd_output([
            "nvme list",
            "nvme list-subsys",
        ])
        for dev in self.get_nvme_devices():
            # runs nvme-cli commands
            self.add_cmd_output([
                "smartctl --all /dev/%s" % dev,
                "nvme list-ns /dev/%s" % dev,
                "nvme fw-log /dev/%s" % dev,
                "nvme list-ctrl /dev/%s" % dev,
                "nvme id-ctrl -H /dev/%s" % dev,
                "nvme id-ns -H /dev/%s" % dev,
                "nvme smart-log /dev/%s" % dev,
                "nvme error-log /dev/%s" % dev,
                "nvme show-regs /dev/%s" % dev,
                "nvme get-ns-id /dev/%s" % dev
            ])
            self.add_copy_spec("/etc/nvme/discovery.conf")

# vim: set et ts=4 sw=4 :
