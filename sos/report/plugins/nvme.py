# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Nvme(Plugin, IndependentPlugin):

    short_desc = 'Collect config and system information about NVMe devices'

    plugin_name = "nvme"
    profiles = ('storage',)
    packages = ('nvme-cli',)

    def setup(self):
        self.add_copy_spec("/etc/nvme/*")
        self.add_cmd_output([
            "nvme list",
            "nvme list-subsys",
        ])

        cmds = [
            "smartctl --all %(dev)s",
            "smartctl --all %(dev)s -j",
            "nvme list-ns %(dev)s",
            "nvme fw-log %(dev)s",
            "nvme list-ctrl %(dev)s",
            "nvme id-ctrl -H %(dev)s",
            "nvme id-ns -H %(dev)s",
            "nvme smart-log %(dev)s",
            "nvme error-log %(dev)s",
            "nvme show-regs %(dev)s"
        ]
        self.add_device_cmd(cmds, devices='block', whitelist='nvme.*')

# vim: set et ts=4 sw=4 :
