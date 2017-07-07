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


class Nvme(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Collect config and system information about NVMe devices"""

    plugin_name = "nvme"
    packages = ('nvme-cli',)

    def get_nvme_devices(self):
        devices = [dev for dev in os.listdir('/sys/block/')
                   if dev.startswith('nvme')]

        return devices

    def check_fw_mode(self, cat_cpuinfo_out):
        """ Recieves the output from 'cat /proc/cpuinfo' and check whether the firmware
        mode is OPAL or not """
        for line in cat_cpuinfo_out.splitlines():
            if "firmware" in line:
                if "OPAL" in line:
                    return True
                else:
                    return False
        return False

    def get_block_size(self, cmd_lsblk_out, dev):
        """ Recieves the output from 'lsblk' and get the block size for the
        specified device"""
        for line in cmd_lsblk_out.splitlines():
            if dev in line:
                return line.split()[3]
        return

    def get_pci_slot_location(self, cmd_lscfg_out, op):
        """ Recieves the output from 'lscfg -vl <device-name>' and get the line
        corresponding to 'mass-storage' or 'pci', depending of the firmware
        mode """
        for line in cmd_lscfg_out.splitlines():
            if op in line:
                return line.split()
        return []

    def setup(self):
        # check if the firmware mode is OPAL
        cat_cpuinfo = self.call_ext_prog("cat /proc/cpuinfo")
        if cat_cpuinfo['status'] == 0:
            is_opal = self.check_fw_mode(cat_cpuinfo['output'])
            if is_opal:
                op = "mass-storage"
            else:
                op = "pci"

        for dev in self.get_nvme_devices():
            # get block size
            cmd_lsblk = self.call_ext_prog("lsblk")
            if cmd_lsblk['status'] == 0:
                blk_size = self.get_block_size(cmd_lsblk['output'], dev)
                self.add_string_as_file(blk_size, "block-size.%s" % dev)

            # get info about slot location and pci location
            cmd_lscfg = self.call_ext_prog("lscfg -vl %s" % dev[0:-2])
            if cmd_lscfg['status'] == 0:
                pci_slot_location = self.get_pci_slot_location(
                                cmd_lscfg['output'], op)

                if pci_slot_location:
                    pci_loc = pci_slot_location[0]
                    slot_loc = pci_slot_location[3]
                    self.add_string_as_file(pci_loc, "pci_loc.%s" % dev)
                    self.add_string_as_file(slot_loc, "slot_loc.%s" % dev)

            # runs nvme-cli commands
            self.add_cmd_output([
                                "nvme list",
                                "nvme list-ns /dev/%s" % dev,
                                "nvme fw-log /dev/%s" % dev,
                                "nvme list-ctrl /dev/%s" % dev,
                                "nvme id-ctrl -H /dev/%s" % dev,
                                "nvme id-ns -H /dev/%s" % dev,
                                "nvme smart-log /dev/%s" % dev,
                                "nvme error-log /dev/%s" % dev,
                                "nvme show-regs /dev/%s" % dev])
