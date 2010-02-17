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
import re
from stat import *

class xen(sos.plugintools.PluginBase):
    """Xen related information
    """
    def determineXenHost(self):
        if os.access("/proc/acpi/dsdt", os.R_OK):
            (status, output, rtime) = self.callExtProg("grep -qi xen /proc/acpi/dsdt")
            if status == 0:
                return "hvm"

        if os.access("/proc/xen/capabilities", os.R_OK):
            (status, output, rtime) = self.callExtProg("grep -q control_d /proc/xen/capabilities")
            if status == 0:
                return "dom0"
            else:
                return "domU"
        return "baremetal"

    def checkenabled(self):
        if self.determineXenHost() == "baremetal":
            return False
        return True

    def is_running_xenstored(self):
        xs_pid = os.popen("pidof xenstored").read()
        xs_pidnum = re.split('\n$',xs_pid)[0]
        return xs_pidnum.isdigit()

    def domCollectProc(self):
        self.addCopySpec("/proc/xen/balloon")
        self.addCopySpec("/proc/xen/capabilities")
        self.addCopySpec("/proc/xen/xsd_kva")
        self.addCopySpec("/proc/xen/xsd_port")
        # determine if CPU has PAE support
        self.collectExtOutput("/bin/grep pae /proc/cpuinfo")
        # determine if CPU has Intel-VT or AMD-V support
        self.collectExtOutput("/bin/egrep -e 'vmx|svm' /proc/cpuinfo")

    def setup(self):
        host_type = self.determineXenHost()
        if host_type == "domU":
            # we should collect /proc/xen and /sys/hypervisor
            self.domCollectProc()
            # determine if hardware virtualization support is enabled
            # in BIOS: /sys/hypervisor/properties/capabilities
            self.addCopySpec("/sys/hypervisor")
        elif host_type == "hvm":
            # what do we collect here???
            pass
        elif host_type == "dom0":
            # default of dom0, collect lots of system information
            self.addCopySpec("/var/log/xen")
            self.addCopySpec("/etc/xen")
            self.collectExtOutput("/usr/sbin/xm dmesg")
            self.collectExtOutput("/usr/sbin/xm info")
            self.collectExtOutput("/usr/sbin/xm list")
            self.collectExtOutput("/usr/sbin/xm list --long")
            self.collectExtOutput("/usr/sbin/brctl show")
            self.domCollectProc()
            self.addCopySpec("/sys/hypervisor/version")
            self.addCopySpec("/sys/hypervisor/compilation")
            self.addCopySpec("/sys/hypervisor/properties")
            self.addCopySpec("/sys/hypervisor/type")
            if self.is_running_xenstored(): 
                self.addCopySpec("/sys/hypervisor/uuid")
                self.collectExtOutput("/usr/bin/xenstore-ls")
            else:
                # we need tdb instead of xenstore-ls if cannot get it.
                self.addCopySpec("/var/lib/xenstored/tdb")

            # FIXME: we *might* want to collect things in /sys/bus/xen*,
            # /sys/class/xen*, /sys/devices/xen*, /sys/modules/blk*,
            # /sys/modules/net*, but I've never heard of them actually being
            # useful, so I'll leave it out for now
        else:
            # for bare-metal, we don't have to do anything special
            return

        self.addCustomText("Xen hostType: "+host_type)
        return

