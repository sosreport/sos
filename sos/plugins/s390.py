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

import os
import sos.plugintools

class s390(sos.plugintools.PluginBase):
    """s390 related information
    """

    ### Check for s390 arch goes here

    def checkenabled(self):
        return (self.policy().getArch() == "s390")

    ### Gather s390 specific information

    def setup(self):
        self.addCopySpecs([
            "/proc/cio_ignore"
            "/proc/crypto",
            "/proc/dasd/devices",
            "/proc/dasd/statistics",
            "/proc/misc",
            "/proc/qeth",
            "/proc/qeth_perf",
            "/proc/qeth_ipa_takeover",
            "/proc/sys/appldata/*",
            "/proc/sys/kernel/hz_timer",
            "/proc/sysinfo",
            "/sys/bus/ccwgroup/drivers/qeth/0.*/*",
            "/sys/bus/ccw/drivers/zfcp/0.*/*",
            "/sys/bus/ccw/drivers/zfcp/0.*/0x*/*",
            "/sys/bus/ccw/drivers/zfcp/0.*/0x*/0x*/*",
            "/etc/zipl.conf",
            "/etc/zfcp.conf",
            "/etc/sysconfig/dumpconf",
            "/etc/src_vipa.conf",
            "/etc/ccwgroup.conf",
            "/etc/chandev.conf"])
        self.collectExtOutput("/sbin/lscss")
        self.collectExtOutput("/sbin/lsdasd")
        self.collectExtOutput("/sbin/lstape")
        self.collectExtOutput("find /sys -type f")
        self.collectExtOutput("find /proc/s390dbf -type f")
        self.collectExtOutput("/sbin/qethconf list_all")
        ret, dasdDev, rtime = self.callExtProg("/bin/ls /dev/dasd?")
        for x in dasdDev.split('\n'):
            self.collectExtOutput("/sbin/dasdview -x -i -j -l -f %s" % (x,))
            self.collectExtOutput("/sbin/fdasd -p %s" % (x,))
        try:
            rhelver = self.policy().rhelVersion()
            if rhelver == 5:
                self.collectExtOutput("/sbin/lsqeth")
                self.collectExtOutput("/sbin/lszfcp")
        except:
            rhelver = None
