# Copyright (C) 2023 Nvidia Corporation, Alin Serdean <aserdean@nvidia.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import time
from sos.report.plugins import Plugin, IndependentPlugin


class MellanoxFirmware(Plugin, IndependentPlugin):

    short_desc = 'Nvidia(Mellanox) firmware tools output'

    plugin_name = "mellanox_firmware"
    profiles = ('hardware', 'system')
    packages = ('mst', 'mstflint')

    MLNX_STRING = "Mellanox Technologies"

    def check_enabled(self):
        """
        Checks if this plugin should be executed at all.
        We will only enable the plugin if there is a
        Mellanox Technologies network adapter
        """
        lspci = self.exec_cmd("lspci -D -d 15b3::0200")
        return lspci['status'] == 0 and self.MLNX_STRING in lspci['output']

    def collect(self):
        if not self.get_option('allow_system_changes'):
            self._log_info("Skipping mst/mlx cable commands as system changes"
                           "would be made. Use --allow-system-changes to"
                           "enable this collection.")
            return

        # Run only if mft package is installed.
        # flint is available from the mft package.
        cout = self.exec_cmd('flint --version')
        if cout['status'] != 0:
            return

        cout = self.collect_cmd_output('mst start')
        if cout['status'] != 0:
            return

        self.collect_cmd_output('mst cable add')
        self.collect_cmd_output("mst status -v", timeout=10)
        self.collect_cmd_output("mlxcables", timeout=10)
        cout = os.listdir("/dev/mst")
        mlxcables = []
        for device in cout:
            if 'cable' in device:
                mlxcables.append(device)
        for mlxcable in mlxcables:
            self.collect_cmd_output(f"mlxcables -d {mlxcable} --DDM",
                                    timeout=10)
            self.collect_cmd_output(f"mlxcables -d {mlxcable} --dump",
                                    timeout=10)
        self.collect_cmd_output("mst stop", changes=True)

    def setup(self):
        # Get all devices which have the vendor Mellanox Technologies
        devices = []
        device_list = self.collect_cmd_output('lspci -D -d 15b3::0200')
        # Will return a string of the following format:
        # 0000:08:00.0 Ethernet controller: Mellanox Technologies MT2892 Family
        if device_list['status'] != 0:
            # bail out if there no Mellanox PCI devices
            return

        for line in device_list["output"].splitlines():
            # Should return 0000:08:00.0
            # from the following string
            # 0000:08:00.0 Ethernet controller: Mellanox Technologies MT2892
            # Family
            devices.append(line[0:8]+'00.0')

        devices = set(devices)

        # Mft package is present if OFED is installed
        # mstflint package is part of the distro and can be installed.
        commands = []

        # mft package is installed if flint command is available
        cout = self.exec_cmd('flint --version')
        if cout['status'] != 0:
            # mstflint package commands
            # the commands do not support position independent arguments
            commands = [
                ["mstconfig -d ", " -e q"],
                ["mstflint -d ", " dc"],
                ["mstflint -d ", " q"],
                ["mstreg -d ", " --reg_name ROCE_ACCL --get"],
                ["mstlink -d ", ""],
            ]
        else:
            # mft package commands
            # the commands do not support position independent arguments
            commands = [
                ["mlxdump -d ", " pcie_uc --all"],
                ["mstconfig -d ", " -e q"],
                ["flint -d ", " dc"],
                ["flint -d ", " q"],
                ["mlxreg -d ", " --reg_name ROCE_ACCL --get"],
                ["mlxlink -d ", ""],
                ["fwtrace -d ", " -i all --tracer_mode FIFO"],
            ]
        for device in devices:
            for command in commands:
                self.add_cmd_output(f"{command[0]} {device} "
                                    f"{command[1]}", timeout=30)

            # Dump the output of the mstdump command three times
            # waiting for one second. This output is useful to check
            # if certain registers changed
            for _ in range(3):
                self.add_cmd_output(f"mstdump {device}")
                time.sleep(1)

# vim: set et ts=4 sw=4 :
