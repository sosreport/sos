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
        _subdir1 = "nvme_smartctl"
        _subdir2 = "nvme_fw_smart_error_logs"

        self.add_copy_spec("/etc/nvme/*")
        self.add_cmd_output([
            "nvme list",
            "nvme list-subsys",
        ])

        smartctl_cmds = [
            "smartctl --all %(dev)s",
            "smartctl --all %(dev)s -j"
        ]

        nvme_logs_cmds = [
            "nvme fw-log %(dev)s",
            "nvme smart-log %(dev)s",
            "nvme error-log %(dev)s"
        ]

        nvme_commands = [
            "nvme list-ns %(dev)s",
            "nvme list-ctrl %(dev)s",
            "nvme id-ctrl -H %(dev)s",
            "nvme id-ns -H %(dev)s",
            "nvme show-regs %(dev)s"
        ]

        subdirs = [
            "nvme_list-ns",
            "nvme_list-ctrl",
            "nvme_id-ctrl_-H",
            "nvme_id-ns_-H",
            "nvme_show-regs"
        ]

        self.add_device_cmd(smartctl_cmds, devices='block', whitelist='nvme.*',
                            subdir=_subdir1)

        self.add_device_cmd(nvme_logs_cmds, devices='block',
                            whitelist='nvme.*', subdir=_subdir2)

        for cmd, dir in zip(nvme_commands, subdirs):
            self.add_device_cmd(cmd, whitelist='nvme.*',
                                devices='block', subdir=dir)

# vim: set et ts=4 sw=4 :
