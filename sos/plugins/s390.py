## Copyright (C) 2007 Red Hat, Inc., Justin Payne <jpayne@redhat.com>

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

import glob
import os
import sos.plugintools

class s390(sos.plugintools.PluginBase):
    """s390 related information
    """

    ### Check for s390 arch goes here

    def checkenabled(self):
        sysArch = self.policy().getArch()
        if "s390" in sysArch:
            return True
        return False

    ### Gather s390 specific information

    def setup(self):
        self.addCopySpec("/proc/cio_ignore")
        self.addCopySpec("/proc/crypto")
        self.addCopySpec("/proc/dasd/devices")
        self.addCopySpec("/proc/dasd/statistics")
        self.addCopySpec("/proc/misc")
        self.addCopySpec("/proc/qeth")
        self.addCopySpec("/proc/qeth_perf")
        self.addCopySpec("/proc/qeth_ipa_takeover")
        self.addCopySpec("/proc/sys/appldata/*")
        self.addCopySpec("/proc/sys/kernel/hz_timer")
        self.addCopySpec("/proc/sysinfo")
        self.addCopySpec("/sys/bus/ccwgroup/drivers/qeth/0.*/*")
        self.addCopySpec("/sys/bus/ccw/drivers/zfcp/0.*/*")
        self.addCopySpec("/sys/bus/ccw/drivers/zfcp/0.*/0x*/*")
        self.addCopySpec("/sys/bus/ccw/drivers/zfcp/0.*/0x*/0x*/*")
        self.addCopySpec("/etc/zipl.conf")
        self.addCopySpec("/etc/zfcp.conf")
        self.addCopySpec("/etc/sysconfig/dumpconf")
        self.addCopySpec("/etc/src_vipa.conf")
        self.addCopySpec("/etc/ccwgroup.conf")
        self.addCopySpec("/etc/chandev.conf")
        self.collectExtOutput("/sbin/lscss")
        self.collectExtOutput("/sbin/lsdasd")
        self.collectExtOutput("/sbin/lstape")
        self.collectExtOutput("find /sys -type f")
        self.collectExtOutput("find /proc/s390dbf -type f")
        self.collectExtOutput("/sbin/qethconf list_all")
        ret, dasdDev, rtime = self.callExtProg("ls /dev/dasd?")
        for x in dasdDev.split('\n'):
            self.collectExtOutput("/sbin/dasdview -x -i -j -l -f %s" % (x,))
            self.collectExtOutput("/sbin/fdasd -p %s" % (x,))
        try:
            rhelver = self.policy().rhelVersion()
            if rhelver == "5":
                self.collectExtOutput("/sbin/lsqeth")
                self.collectExtOutput("/sbin/lszfcp")
        except:
            rhelver = None
