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
    def collect(self):
        self.copyFileOrDir("/proc/partitions")
        self.copyFileOrDir("/proc/cpuinfo")
        self.copyFileOrDir("/proc/meminfo")
        self.copyFileOrDir("/proc/ioports")
        self.copyFileOrDir("/proc/interrupts")
        self.copyFileOrDir("/proc/scsi")
        self.copyFileOrDir("/proc/dma")
        self.copyFileOrDir("/proc/devices")
        self.copyFileOrDir("/proc/rtc")
        self.copyFileOrDir("/proc/ide")
        self.copyFileOrDir("/proc/bus")
        self.copyFileOrDir("/etc/stinit.def")
        self.copyFileOrDir("/etc/sysconfig/hwconf")
        self.copyFileOrDir("/proc/chandev")
        self.copyFileOrDir("/proc/dasd")
        self.copyFileOrDir("/proc/s390dbf/tape")
        self.runExe("/usr/share/rhn/up2dateclient/hardware.py")
        self.runExe("/sbin/lspci -vvn")
        self.runExe("dmesg | grep -e 'e820.' -e 'agp.'")
              
        for hwmodule in commands.getoutput('cat pcitable | grep -v "Card:" | awk \'{ gsub("\"","",$0); { print $NF; };} \' | uniq -u'):
          cmdToRun = "dmesg | grep %s" % (hwmodule,)
          self.runExe(cmdToRun)        
          
        self.runExe("/usr/sbin/vgdisplay -vv")
        self.runExe("/sbin/lsusb")
        self.runExe("/usr/bin/lshal")
        return

