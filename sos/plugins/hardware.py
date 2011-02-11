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
from glob import glob

class hardware(sos.plugintools.PluginBase):
    """hardware related information
    """
    def setup(self):
        self.addCopySpecs([
            "/proc/partitions",
            "/proc/cpuinfo",
            "/proc/meminfo",
            "/proc/ioports",
            "/proc/interrupts",
            "/proc/scsi",
            "/proc/dma",
            "/proc/devices",
            "/proc/rtc",
            "/proc/ide",
            "/proc/bus",
            "/etc/stinit.def",
            "/proc/chandev",
            "/proc/dasd",
            "/proc/s390dbf/tape",
            "/sys/bus/scsi",
            "/sys/state"])
        self.collectExtOutput(glob("/usr/share/rhn/up2date*client/hardware.py")[0]) # RHBZ#572353
        self.collectExtOutput("""/bin/echo -e "lspci:\n" ; /sbin/lspci ; /bin/echo -e "\nlspci -nvv:\n" ; /sbin/lspci -nvv ; /bin/echo -e "\nlspci -tv:\n" ; /sbin/lspci -tv""", suggest_filename = "lspci", root_symlink = "lspci")

        self.collectExtOutput("/usr/sbin/dmidecode", root_symlink = "dmidecode")

        if self.policy().getArch().endswith("386"):
            self.collectExtOutput("/usr/sbin/x86info -a")

        self.collectExtOutput("/sbin/lsusb")
        self.collectExtOutput("/usr/bin/lshal")
        self.collectExtOutput("/usr/bin/systool -c fc_host -v")
        self.collectExtOutput("/usr/bin/systool -c scsi_host -v")
