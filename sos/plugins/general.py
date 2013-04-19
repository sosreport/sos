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

class General(Plugin):
    """basic system information"""

    plugin_name = "general"

    option_list = [("syslogsize", "max size (MiB) to collect per syslog file", "", 15),
                  ("all_logs", "collect all log files defined in syslog.conf", "", False)]

    def setup(self):
        self.add_copy_specs([
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
            "/etc/localtime",
            "/root/anaconda-ks.cfg"])

        limit = self.get_option("syslogsize")
        self.add_cmd_output("dmesg", suggest_filename="dmesg_now")
        self.add_copy_spec_limit("/var/log/messages*", sizelimit = limit)
        self.add_copy_spec_limit("/var/log/secure*", sizelimit = limit)
        self.add_cmd_output("hostid")
        self.add_cmd_output("hostname", root_symlink="hostname")
        self.add_cmd_output("date", root_symlink="date")
        self.add_cmd_output("uptime", root_symlink="uptime")
        self.add_cmd_output("dmesg")
        self.add_cmd_output("alternatives --display java",
                                root_symlink="java")
        self.add_cmd_output("readlink -f /usr/bin/java")
        self.add_cmd_output("tree /var/lib")
        self.add_cmd_output("ls -lR /var/lib")


class RedHatGeneral(General, RedHatPlugin):
    """Basic system information for RedHat based distributions"""

    def setup(self):
        super(RedHatGeneral, self).setup()

        self.add_copy_specs([
            "/etc/redhat-release",
            "/etc/fedora-release",
        ])

        if self.get_option('all_logs'):
            print "doing all_logs..."
            limit = self.option_enabled("syslogsize")
            logs = self.do_regex_find_all("^\S+\s+(-?\/.*$)\s+",
                                "/etc/syslog.conf")
            print logs
            if self.policy().pkg_by_name("rsyslog") \
              or os.path.exists("/etc/rsyslog.conf"):
                logs += self.do_regex_find_all("^\S+\s+(-?\/.*$)\s+", "/etc/rsyslog.conf")
                print logs
            for i in logs:
                if i.startswith("-"):
                    i = i[1:]
                if os.path.isfile(i):
                    self.add_copy_spec_limit(i, sizelimit = limit)


    def postproc(self):
        self.do_file_sub("/etc/sysconfig/rhn/up2date",
                r"(\s*proxyPassword\s*=\s*)\S+", r"\1***")


class DebianGeneral(General, DebianPlugin):
    """Basic system information for Debian based distributions"""

    def setup(self):
        super(DebianGeneral, self).setup()
        self.add_copy_specs([
            "/etc/debian_version",
            "/etc/default",
            "/etc/lsb-release"
        ])
class UbuntuGeneral(General, UbuntuPlugin):
    """Basic system information for Ubuntu based distributions"""

    def setup(self):
        super(UbuntuGeneral, self).setup()
        self.add_copy_specs([
            "/etc/default",
            "/etc/lsb-release",
            "/etc/os-release",
            "/var/log/apport.log",
            "/var/log/syslog",
            "/var/log/udev",
            "/var/log/boot*",
            "/var/log/dmesg*",
            "/var/log/kern*",
            "/var/log/mail*",
            "/var/log/dist-upgrade",
            "/var/log/landscape",
            "/var/log/installer",
            "/var/log/unattended-upgrades",
            "/var/log/upstart"
        ])

