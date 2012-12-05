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
from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin

class general(Plugin):
    """basic system information"""

    plugin_name = "general"

    optionList = [("syslogsize", "max size (MiB) to collect per syslog file", "", 15),
                  ("all_logs", "collect all log files defined in syslog.conf", "", False)]

    def setup(self):
        self.addCopySpecs([
            "/etc/init",    # upstart
            "/etc/event.d", # "
            "/etc/inittab",
            "/etc/sos.conf",
            "/etc/sysconfig",
            "/proc/stat",
            "/var/log/dmesg",
            "/var/log/sa",
            "/var/log/pm/suspend.log",
            "/var/log/up2date",
            "/etc/hostid",
            "/var/lib/dbus/machine-id",
            "/etc/exports",
            "/root/anaconda-ks.cfg"])

        limit = self.getOption("syslogsize")
        self.collectExtOutput("/bin/dmesg", suggest_filename="dmesg_now")
        self.addCopySpecLimit("/var/log/messages*", sizelimit = limit)
        self.addCopySpecLimit("/var/log/secure*", sizelimit = limit)
        self.collectExtOutput("/usr/bin/hostid")
        self.collectExtOutput("/bin/hostname", root_symlink="hostname")
        self.collectExtOutput("/bin/date", root_symlink="date")
        self.collectExtOutput("/usr/bin/uptime", root_symlink="uptime")
        self.collectExtOutput("/bin/dmesg")
        self.collectExtOutput("/usr/sbin/alternatives --display java",
                                root_symlink="java")
        self.collectExtOutput("/usr/bin/readlink -f /usr/bin/java")


class RedHatGeneral(general, RedHatPlugin):
    """Basic system information for RedHat based distributions"""

    def setup(self):
        super(RedHatGeneral, self).setup()

        self.addCopySpecs([
            "/etc/redhat-release",
            "/etc/fedora-release",
        ])

        if self.getOption('all_logs'):
            print "doing all_logs..."
            limit = self.isOptionEnabled("syslogsize")
            logs = self.doRegexFindAll("^\S+\s+(-?\/.*$)\s+",
                                "/etc/syslog.conf")
            print logs
            if self.policy().pkgByName("rsyslog") \
              or os.path.exists("/etc/rsyslog.conf"):
                logs += self.doRegexFindAll("^\S+\s+(-?\/.*$)\s+", "/etc/rsyslog.conf")
                print logs
            for i in logs:
                if i.startswith("-"):
                    i = i[1:]
                if os.path.isfile(i):
                    self.addCopySpecLimit(i, sizelimit = limit)


    def postproc(self):
        self.doFileSub("/etc/sysconfig/rhn/up2date",
                r"(\s*proxyPassword\s*=\s*)\S+", r"\1***")


class GeneralDebian(general, DebianPlugin, UbuntuPlugin):
    """Basic system information for Debian based distributions"""

    def setup(self):
        super(GeneralDebian, self).setup()
        self.addCopySpecs([
            "/etc/debian_version",
            "/var/log/up2date",
            "/etc/lsb-release"
        ])
