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
from sos.plugins import Plugin, RedHatPlugin

class s390(Plugin, RedHatPlugin):
    """s390 related information
    """

    ### Check for s390 arch goes here

    def check_enabled(self):
        return (self.policy().getArch() == "s390")

    ### Gather s390 specific information

    def setup(self):
        self.add_copy_specs([
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
        self.add_cmd_output("/sbin/lscss")
        self.add_cmd_output("/sbin/lsdasd")
        self.add_cmd_output("/sbin/lstape")
        self.add_cmd_output("find /sys -type f")
        self.add_cmd_output("find /proc/s390dbf -type f")
        self.add_cmd_output("/sbin/qethconf list_all")
        ret, dasdDev, rtime = self.call_ext_prog("/bin/ls /dev/dasd?")
        for x in dasdDev.split('\n'):
            self.add_cmd_output("/sbin/dasdview -x -i -j -l -f %s" % (x,))
            self.add_cmd_output("/sbin/fdasd -p %s" % (x,))
        try:
            rhelver = self.policy().rhelVersion()
            if rhelver == 5:
                self.add_cmd_output("/sbin/lsqeth")
                self.add_cmd_output("/sbin/lszfcp")
        except:
            rhelver = None
