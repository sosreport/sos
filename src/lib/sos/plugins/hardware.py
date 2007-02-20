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
import commands

class hardware(sos.plugintools.PluginBase):
    """This plugin gathers hardware related information
    """
    def setup(self):
        self.addCopySpec("/proc/partitions")
        self.addCopySpec("/proc/cpuinfo")
        self.addCopySpec("/proc/meminfo")
        self.addCopySpec("/proc/ioports")
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
        self.collectExtOutput("/usr/share/rhn/up2dateclient/hardware.py")
        self.collectExtOutput("/sbin/lspci -vvn")
        self.collectExtOutput("dmesg | grep -e 'e820.' -e 'agp.'")
              
        for hwmodule in commands.getoutput('cat pcitable | grep -v "Card:" | awk \'{ gsub("\"","",$0); { print $NF; };} \' | uniq -u'):
          cmdToRun = "dmesg | grep %s" % (hwmodule,)
          self.collectExtOutput(cmdToRun)        
          
        self.collectExtOutput("/sbin/lsusb")
        self.collectExtOutput("/usr/bin/lshal")
        return

