# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Nvme(Plugin, IndependentPlugin):
    """Collects nvme device configuration information for each nvme device that
    is installed on the system.

    Basic information is collected via the `smartctl` utility, however detailed
    information will be collected via the `nvme` CLI if the `nvme-cli` package
    is installed.
    """

    short_desc = 'NVMe device information'

    plugin_name = "nvme"
    profiles = ('storage',)
    packages = ('nvme-cli',)
    kernel_mods = ('nvme', 'nvme_core')

    def setup(self):
        self.add_copy_spec([
            "/etc/nvme/*",
            "/sys/class/nvme-fabrics/ctl/nvme*",
            "/sys/class/nvme-subsystem/nvme-subsys*/*",
            "/sys/module/nvme_core/parameters/*",
        ])

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
