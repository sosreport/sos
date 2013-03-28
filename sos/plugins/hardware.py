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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
from glob import glob
import os

class hardware(Plugin):
    """hardware related information
    """

    plugin_name = "hardware"

    def setup(self):
        self.add_copy_specs([
            "/proc/partitions",
            "/proc/cpuinfo",
            "/proc/meminfo",
            "/proc/ioports",
            "/proc/iomem",
            "/proc/interrupts",
            "/proc/irq",
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
            "/sys/state",
            "/sys/firmware/acpi/tables",
            "/var/log/mcelog"])
        self.add_cmd_output("""/bin/echo -e "lspci:\n" ; /sbin/lspci ; /bin/echo -e "\nlspci -nvv:\n" ; /sbin/lspci -nvv ; /bin/echo -e "\nlspci -tv:\n" ; /sbin/lspci -tv""", suggest_filename = "lspci", root_symlink = "lspci")

        self.add_cmd_output("/usr/sbin/dmidecode", root_symlink = "dmidecode")

	if os.path.exists("/usr/bin/cpufreq-info"):
	        self.add_cmd_output("/usr/bin/cpufreq-info")
	if os.path.exists("/usr/bin/cpupower"):
		self.add_cmd_output("/usr/bin/cpupower info")
		self.add_cmd_output("/usr/bin/cpupower frequency-info")

        if self.policy().getArch().endswith("386"):
            self.add_cmd_output("/usr/sbin/x86info -a")

        if os.path.exists("/usr/bin/lsusb"):
            lsusb_path = "/usr/bin/lsusb"
        else:
            lsusb_path = "/usr/bin/lsusb"

        self.add_cmd_output("%s"% lsusb_path)
        self.add_cmd_output("%s -v"% lsusb_path)
        self.add_cmd_output("%s -t"% lsusb_path)

        self.add_cmd_output("/usr/bin/lshal")
        self.add_cmd_output("/usr/bin/systool -c fc_host -v")
        self.add_cmd_output("/usr/bin/systool -c scsi_host -v")

class RedHatHardware(hardware, RedHatPlugin):
    """hardware related information for Red Hat distribution
    """

    def setup(self):
        super(RedHatHardware, self).setup()
        hwpaths = glob("/usr/share/rhn/up2date*client/hardware.py")
	if (len(hwpaths) == 0):
            return
        self.add_cmd_output(hwpaths[0])


class DebianHardware(hardware, DebianPlugin, UbuntuPlugin):
    """hardware related information for Debian distribution
    """

    def setup(self):
        super(DebianHardware, self).setup()
