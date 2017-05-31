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
import os, subprocess

class NvmePlugin(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Collect config and system information about NVMe devices"""

    plugin_name = "nvme"
    devices = [] 

    def copy_spec(self):
        """ Loop through all NVMe devices in /sys/block/<nvme-device>/ 
	and get the files inside queue/, device/, integrity/ and mq/ """

        i = 0
        while os.path.isdir('/sys/block/nvme%dn1' % i):
            self.devices.append("nvme%dn1" % i)

            queue_files = subprocess.check_output("ls -1 /sys/block/nvme%dn1/queue/*" % i, shell=True).rstrip()
            # in python 3.3 or above the prefix b' is not ignored, so bytes.decode() is used to get rid of it
            queue_files = bytes.decode(queue_files)
            queue_files = queue_files.splitlines()
            for q in queue_files:
                self.add_copy_spec(q)

            device_files = subprocess.check_output("find /sys/block/nvme%dn1/device/ -maxdepth 1 -type f" % i, shell=True).rstrip()
            device_files = bytes.decode(device_files)
            device_files = device_files.splitlines()
            for d in device_files:
                self.add_copy_spec(d)

            general_files = subprocess.check_output("find /sys/block/nvme%dn1/ -maxdepth 1 -type f" % i, shell=True).rstrip()
            general_files = bytes.decode(general_files)
            general_files = general_files.splitlines()
            for g in general_files:
                self.add_copy_spec(g)

            integrity_files = subprocess.check_output("ls -1 /sys/block/nvme%dn1/integrity/*" % i, shell=True).rstrip()
            integrity_files = bytes.decode(integrity_files)
            integrity_files = integrity_files.splitlines()
            for ing in integrity_files:
                self.add_copy_spec(ing)

            mq_files = subprocess.check_output("find /sys/block/nvme%dn1/mq/ -type f" % i, shell=True).rstrip()
            mq_files = bytes.decode(mq_files)
            mq_files = mq_files.splitlines()
            for m in mq_files:
                self.add_copy_spec(m)	

            i += 1

    def setup(self):
        self.copy_spec()

        for dev in self.devices:
            # get block size
            self.add_cmd_output("sh -c \"lsblk | grep %s | awk '{ print $4 }'\"" % dev, suggest_filename="block-size.%s" % dev)

            # check if the firmware mode is OPAL
            opal = subprocess.check_output("cat /proc/cpuinfo | grep firmware | grep OPAL | wc -l", shell=True)
            opal = int(opal)
            if opal == 1:
                grep_op = "mass-storage"
            else:
                grep_op = "pci"

            # get info about slot location and pci location
            slot = subprocess.check_output("lscfg -vl %s | grep nvme | grep %s | awk '{ print $4 }'"
                % (dev[0:-2], grep_op), shell=True).strip()
            pci = subprocess.check_output("lscfg -vl %s | grep nvme | grep %s | awk '{ print $1 }'" 
                % (dev[0:-2], grep_op), shell=True).strip()

            # add slot and pci location in sos_strings/nvme/
            self.add_string_as_file(slot, "slot_location.%s" % dev)
            self.add_string_as_file(pci, "pci_location.%s" % dev)

            # get PCI Vendor ID
            self.add_cmd_output("sh -c \"lspci -vs %s | grep 'Non-Volatile memory controller' | cut -c 46-\"" 
                % pci, suggest_filename="pci_vdid.%s" % dev)

            # get Subsystem ID
            self.add_cmd_output("sh -c \"lspci -vs %s | grep Subsystem | cut -c 13-\"" 
                % pci, suggest_filename="pci_ssid.%s" % dev)

            # get Part Number
            self.add_cmd_output("sh -c \"lspci -vvs %s | grep '\[PN\]' | awk '{ print $4 }'\"" 
                % pci, suggest_filename="part-number.%s" % dev)

            # get Engineering Changes [EC] code
            self.add_cmd_output("sh -c \"lspci -vvs %s | grep '\[EC\]' | awk '{ print $4 }'\"" 
                % pci, suggest_filename="engineering-changes.%s" % dev)

            # check if nvme-cli package is installed
            if self.is_installed("nvme-cli"):
                self.add_cmd_output("nvme list")
                self.add_cmd_output("nvme list-ns /dev/%s" % dev, suggest_filename="list-ns.%s" % dev)
                self.add_cmd_output("nvme fw-log /dev/%s" % dev, suggest_filename="fw-log.%s" % dev)
                self.add_cmd_output("nvme list-ctrl /dev/%s" % dev, suggest_filename="list-ctrl.%s" % dev)
                self.add_cmd_output("nvme id-ctrl -H /dev/%s" % dev, suggest_filename="id-ctrl.%s" % dev)
                self.add_cmd_output("nvme id-ns -H /dev/%s" % dev, suggest_filename="id-ns.%s" % dev)
                self.add_cmd_output("nvme smart-log /dev/%s" % dev, suggest_filename="smart-log.%s" % dev)
                self.add_cmd_output("nvme error-log /dev/%s" % dev, suggest_filename="error-log.%s" % dev)

            else:
                self.add_string_as_file(("The nvme-cli tool is not installed. If you want more configuration details and" 
                    " system information about NVMe devices, you should install it.\n"), "nvme-cli_not_installed")	
