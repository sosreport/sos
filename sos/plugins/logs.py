# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Logs(Plugin):
    """System logs"""

    plugin_name = "logs"
    profiles = ('system', 'hardware')

    def setup(self):
        self.add_copy_spec([
            "/etc/syslog.conf",
            "/etc/rsyslog.conf"
        ])

        self.limit = self.get_option("log_size")
        self.add_copy_spec_limit("/var/log/boot.log", sizelimit=self.limit)
        self.add_copy_spec_limit("/var/log/cloud-init*", sizelimit=self.limit)
        self.add_cmd_output([
            "journalctl --all --this-boot --no-pager",
            "journalctl --all --this-boot --no-pager -o verbose",
        ])

        if self.get_option('all_logs'):
            logs = self.do_regex_find_all("^\S+\s+(-?\/.*$)\s+",
                                          "/etc/syslog.conf")
            if self.is_installed("rsyslog") \
                    or os.path.exists("/etc/rsyslog.conf"):
                logs += self.do_regex_find_all("^\S+\s+(-?\/.*$)\s+",
                                               "/etc/rsyslog.conf")
            for i in logs:
                if i.startswith("-"):
                    i = i[1:]
                if os.path.isfile(i):
                    self.add_copy_spec_limit(i, sizelimit=self.limit)


class RedHatLogs(Logs, RedHatPlugin):

    option_list = [
        ("log_days", "the number of days logs to collect", "", 3)
    ]

    def setup(self):
        super(RedHatLogs, self).setup()
        messages = "/var/log/messages"
        self.add_copy_spec_limit("/var/log/secure*", sizelimit=self.limit)
        self.add_copy_spec_limit(messages + "*", sizelimit=self.limit)
        # collect five days worth of logs by default if the system is
        # configured to use the journal and not /var/log/messages
        if not os.path.exists(messages) and self.is_installed("systemd"):
            try:
                days = int(self.get_option("log_days"))
            except:
                days = 3
            if self.get_option("all_logs"):
                since_opt = ""
            else:
                since_opt = '--since="-%ddays"' % days
            self.add_cmd_output('journalctl --all %s' % since_opt)


class DebianLogs(Logs, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianLogs, self).setup()
        self.add_copy_spec([
            "/var/log/syslog",
            "/var/log/udev",
            "/var/log/kern*",
            "/var/log/mail*",
            "/var/log/dist-upgrade",
            "/var/log/installer",
            "/var/log/unattended-upgrades",
            "/var/log/apport.log",
            "/var/log/landscape"
        ])


# vim: et ts=4 sw=4
