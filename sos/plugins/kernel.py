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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os, re

class kernel(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """kernel related information
    """
    optionList = [("modinfo", 'gathers information on all kernel modules', 'fast', True)]
    moduleFile = ""

    def setup(self):
        self.collectExtOutput("/bin/uname -a", root_symlink = "uname")
        self.moduleFile = self.collectOutputNow("/sbin/lsmod", root_symlink = "lsmod")

        if self.getOption('modinfo'):
            runcmd = ""
            ret, mods, rtime = self.callExtProg('/sbin/lsmod | /bin/cut -f1 -d" " 2>/dev/null | /bin/grep -v Module 2>/dev/null')
            for kmod in mods.split('\n'):
                if '' != kmod.strip():
                    runcmd = runcmd + " " + kmod
            if len(runcmd):
                self.collectExtOutput("/sbin/modinfo " + runcmd)

        self.collectExtOutput("/sbin/sysctl -a")
        if os.path.isfile("/sbin/ksyms"):
            self.collectExtOutput("/sbin/ksyms")
        self.addCopySpecs([
            "/proc/sys/kernel/random/boot_id",
            "/sys/module/*/parameters",
            "/sys/module/*/initstate",
            "/sys/module/*/refcnt",
            "/sys/module/*/taint",
            "/proc/filesystems",
            "/proc/ksyms",
            "/proc/slabinfo",
            "/lib/modules/%s/modules.dep" % self.policy().kernelVersion(),
            "/etc/conf.modules",
            "/etc/modules.conf",
            "/etc/modprobe.conf",
            "/etc/modprobe.d",
            "/etc/sysctl.conf",
            "/etc/sysctl.d",
            "/lib/sysctl.d",
            "/proc/cmdline",
            "/proc/driver",
            "/proc/zoneinfo",
            "/proc/sys/kernel/tainted",
            "/proc/buddyinfo",
            "/proc/softirqs",
            "/proc/timer*",
            "/proc/lock*"])

        self.collectExtOutput("/usr/sbin/dkms status")
