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
        rhelver = self.policy().rhelVersion()
        self.addCopySpec("/etc/redhat-release")
        self.addCopySpec("/etc/fedora-release")
        self.addCopySpec("/etc/inittab")
        self.addCopySpec("/etc/init")
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
        self.addCopySpec("/etc/exports")        
        self.collectExtOutput("/bin/hostname", symlink = "hostname")
        self.collectExtOutput("/bin/date", symlink = "date")
        self.collectExtOutput("/usr/bin/uptime", symlink = "uptime")
        self.collectExtOutput("/bin/dmesg")
        self.collectExtOutput("/usr/sbin/alternatives --display java", symlink = "java")
        self.collectExtOutput("/usr/bin/readlink -f /usr/bin/java")

        # new entitlement certificate support
        if rhelver == 6 or rhelver == 5:
                self.addCopySpec("/etc/pki/product/*.pem")
                self.addCopySpec("/etc/pki/consumer/cert.pem")
                self.addCopySpec("/etc/pki/entitlement/*.pem")
                self.addForbiddenPath("/etc/pki/entitlement/key.pem")
                self.addForbiddenPath("/etc/pki/entitlement/*-key.pem")
                self.addCopySpec("/etc/rhsm/")
                self.addCopySpec("/var/log/rhsm/rhsm.log")
                self.addCopySpec("/var/log/rhsm/rhsmcertd.log")
                self.collectExtOutput("subscription-manager list --installed")
                self.collectExtOutput("subscription-manager list --consumed")

        if self.getOption('all_logs'):
            logs = self.doRegexFindAll("^\S+\s+(-?\/.*$)\s+", "/etc/syslog.conf")
            if self.cInfo["policy"].pkgByName("rsyslog") or os.path.exists("/etc/rsyslog.conf"):
                logs += self.doRegexFindAll("^\S+\s+(-?\/.*$)\s+", "/etc/rsyslog.conf")
            for i in logs:
                if i.startswith("-"):
                    i = i[1:]
                if os.path.isfile(i):
                    self.addCopySpecLimit(i, sizelimit = self.isOptionEnabled("syslogsize"))
        return

    def postproc(self):
        self.doRegexSub("/etc/sysconfig/rhn/up2date", r"(\s*proxyPassword\s*=\s*)\S+", r"\1***")
        return
