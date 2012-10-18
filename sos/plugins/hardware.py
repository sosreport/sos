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

import sos.plugintools
import os

class hardware(sos.plugintools.PluginBase):
    """hardware related information
    """
    def setup(self):
        self.addCopySpec("/proc/partitions")
        self.addCopySpec("/proc/cpuinfo")
        self.addCopySpec("/proc/meminfo")
        self.addCopySpec("/proc/ioports")
        self.addCopySpec("/proc/iomem")
        self.addCopySpec("/proc/interrupts")
        self.addCopySpec("/proc/scsi")
        self.addCopySpec("/proc/dma")
        self.addCopySpec("/proc/devices")
        self.addCopySpec("/proc/rtc")
        self.addCopySpec("/proc/ide")
        self.addCopySpec("/proc/bus")
        self.addCopySpec("/etc/stinit.def")
        self.addCopySpec("/etc/sysconfig/hwconf")
        self.addCopySpec("/proc/chandev")
        self.addCopySpec("/proc/dasd")
        self.addCopySpec("/proc/s390dbf/tape")
        self.addCopySpec("/sys/bus/scsi")
        self.addCopySpec("/sys/state")
        self.addCopySpec("/var/log/mcelog")
        self.collectExtOutput("python /usr/share/rhn/up2date_client/hardware.py", suggest_filename="hardware.py")
        self.collectExtOutput("""/bin/echo -e "lspci:\n" ; /sbin/lspci ; /bin/echo -e "\nlspci -nvv:\n" ; /sbin/lspci -nvv ; /bin/echo -e "\nlspci -tv:\n" ; /sbin/lspci -tv""", suggest_filename = "lspci", symlink = "lspci")

        self.collectExtOutput("/usr/sbin/dmidecode", symlink = "dmidecode")
	self.collectExtOutput("/usr/bin/cpufreq-info")

        if self.policy().getArch().endswith("386"):
            self.collectExtOutput("/usr/sbin/x86info -a")

        if os.path.exists("/usr/bin/lsusb"):
            self.collectExtOutput("/usr/bin/lsusb")
            self.collectExtOutput("/usr/bin/lsusb -v")
            self.collectExtOutput("/usr/bin/lsusb -t 2>&1", suggest_filename = "lsusb_-t")
        elif os.path.exists("/sbin/lsusb"):  
            self.collectExtOutput("/sbin/lsusb")
            self.collectExtOutput("/sbin/lsusb -v")
            self.collectExtOutput("/sbin/lsusb -t 2>&1", suggest_filename = "lsusb_-t")
        self.collectExtOutput("/usr/bin/lshal")
        self.collectExtOutput("/usr/bin/systool -c fc_host -v")
        self.collectExtOutput("/usr/bin/systool -c scsi_host -v")
        return

