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
import glob
import commands

class general(sos.plugintools.PluginBase):
    """basic system information
    """

    optionList = [("syslogsize", "max size (MiB) to collect per syslog file", "", 15),
                  ("all_logs", "collect all log files defined in syslog.conf", "", False)]

    def setup(self):
        self.addCopySpec("/etc/redhat-release")
        self.addCopySpec("/etc/fedora-release")
        self.addCopySpec("/etc/inittab")
        self.addCopySpec("/etc/sos.conf")
        self.addCopySpec("/etc/sysconfig")
        self.addCopySpec("/proc/stat")
        # Capture dmesg from system start
        self.addCopySpec("/var/log/dmesg")
        # Capture second dmesg from time of sos run
        self.collectExtOutput("/bin/dmesg", suggest_filename="dmesg_now")
        self.addCopySpecLimit("/var/log/messages*", sizelimit = self.getOption("syslogsize"))
        self.addCopySpecLimit("/var/log/secure*", sizelimit = self.getOption("syslogsize"))
        self.addCopySpec("/var/log/sa")
        self.addCopySpec("/var/log/pm/suspend.log")
        self.addCopySpec("/var/log/up2date")
        self.collectExtOutput("/usr/bin/hostid")
        self.addCopySpec("/etc/hostid")        
        self.addCopySpec("/var/lib/dbus/machine-id")
        self.addCopySpec("/etc/exports")        
        self.collectExtOutput("/bin/hostname", root_symlink = "hostname")
        self.collectExtOutput("/bin/date", root_symlink = "date")
        self.collectExtOutput("/usr/bin/uptime", root_symlink = "uptime")
        self.collectExtOutput("/bin/dmesg")
        self.addCopySpec("/root/anaconda-ks.cfg")
        self.collectExtOutput("/usr/sbin/alternatives --display java", root_symlink = "java")
        self.collectExtOutput("/usr/bin/readlink -f /usr/bin/java")

        if self.getOption('all_logs'):
            rhelver = self.policy().rhelVersion()
            if rhelver == 5 or rhelver == 4:
                logs=self.doRegexFindAll(r"^\S+\s+(\/.*log.*)\s+$", "/etc/syslog.conf")
                for i in logs:
                    if not os.path.isfile(i): continue
                    self.addCopySpec(i)

            if rhelver == 6:
                logs=self.doRegexFindAll(r"^\S+\s+(\/.*log.*)\s+$", "/etc/rsyslog.conf")
                for i in logs:
                    if not os.path.isfile(i): continue
                    self.addCopySpec(i)

    def postproc(self):
        self.doRegexSub("/etc/sysconfig/rhn/up2date", r"(\s*proxyPassword\s*=\s*)\S+", r"\1***")
