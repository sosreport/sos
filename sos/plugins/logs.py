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
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Logs(Plugin):
    """log data """

    plugin_name = "logs"

    option_list = [
        ("logsize",
            "max size (MiB) to collect per syslog file", "", 15),
        ("all_logs",
            "collect all log files defined in syslog.conf",
            "", False)
    ]

    def setup(self):
        self.limit = self.get_option("syslogsize")
        self.add_copy_spec_limit("/var/log/boot*", sizelimit = self.limit)

        if self.get_option('all_logs'):
            print "doing all_logs..."
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
                    self.add_copy_spec_limit(i, sizelimit = self.limit)


class RedHatLogs(Logs, RedHatPlugin):
    """Basic system information for RedHat based distributions"""

    def setup(self):
        super(RedHatLogs, self).setup()
        self.add_copy_spec_limit("/var/log/secure*", sizelimit = self.limit)
        self.add_copy_spec_limit("/var/log/messages*", sizelimit = self.limit)


class DebianLogs(Logs, DebianPlugin):
    """Basic system information for Debian based distributions"""

    def setup(self):
        super(DebianLogs, self).setup()
        self.add_copy_specs([
            "/var/log/syslog",
            "/var/log/udev",
            "/var/log/kern*",
            "/var/log/mail*",
            "/var/log/dist-upgrade",
            "/var/log/installer",
            "/var/log/unattended-upgrades"
        ])
 

class UbuntuLogs(Logs, UbuntuPlugin):
    """Basic system information for Ubuntu based distributions"""

    def setup(self):
        super(UbuntuLogs, self).setup()
        self.add_copy_specs([
            "/var/log/apport.log",
            "/var/log/landscape",
        ])

