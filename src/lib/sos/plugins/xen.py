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
import os, commands
from stat import *

class xen(sos.plugintools.PluginBase):
    def determineXenHost(self):
        if os.access("/proc/acpi/dsdt", os.R_OK):
            (status, output) = commands.getstatusoutput("/usr/bin/strings /proc/acpi/dsdt | grep -q int-xen")
            if status == 0:
                return "hvm"

        if os.access("/proc/xen/capabilities", os.R_OK):
            (status, output) = commands.getstatusoutput("grep -q control_d /proc/xen/capabilities")
            if status == 0:
                return "dom0"
            else:
                return "domU"
        return "baremetal"

    def domCollectProc(self):
        self.addCopySpec("/proc/xen/balloon")
        self.addCopySpec("/proc/xen/capabilities")
        self.addCopySpec("/proc/xen/xsd_kva")
        self.addCopySpec("/proc/xen/xsd_port")

    def setup(self):
        host_type = self.determineXenHost()
        if host_type == "domU":
            # we should collect /proc/xen and /sys/hypervisor
            self.domCollectProc()
            self.addCopySpec("/sys/hypervisor")
        elif host_type == "hvm":
            # what do we collect here???
            pass
        elif host_type == "dom0":
            # default of dom0, collect lots of system information
            self.addCopySpec("/var/log/xen")
            self.addCopySpec("/etc/xen")
            self.collectExtOutput("/usr/bin/xenstore-ls")
            self.collectExtOutput("/usr/sbin/xm dmesg")
            self.collectExtOutput("/usr/sbin/xm info")
            self.domCollectProc()
            self.addCopySpec("/sys/hypervisor")
            # FIXME: we *might* want to collect things in /sys/bus/xen*,
            # /sys/class/xen*, /sys/devices/xen*, /sys/modules/blk*,
            # /sys/modules/net*, but I've never heard of them actually being
            # useful, so I'll leave it out for now
        else:
            # for bare-metal, we don't have to do anything special
            return

        self.addCustomText("Xen hostType: "+host_type)
        return

