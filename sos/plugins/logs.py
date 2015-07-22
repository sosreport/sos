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
    profiles = ('system', 'hardware', 'storage')

    def setup(self):
        self.add_copy_spec([
            "/etc/syslog.conf",
            "/etc/rsyslog.conf",
            "/etc/rsyslog.d"
        ])

        self.limit = self.get_option("log_size")
        self.add_copy_spec_limit("/var/log/boot.log", sizelimit=self.limit)
        self.add_copy_spec_limit("/var/log/cloud-init*", sizelimit=self.limit)
        self.add_cmd_output([
            "journalctl --all --this-boot --no-pager",
            "journalctl --all --this-boot --no-pager -o verbose",
        ])

        if self.get_option('all_logs'):
            syslog_conf = self.join_sysroot("/etc/syslog.conf")
            logs = self.do_regex_find_all("^\S+\s+(-?\/.*$)\s+", syslog_conf)
            if self.is_installed("rsyslog") \
                    or os.path.exists("/etc/rsyslog.conf"):
                rsyslog_conf = self.join_sysroot("/etc/rsyslog.conf")
                logs += self.do_regex_find_all("^\S+\s+(-?\/.*$)\s+",
                                               rsyslog_conf)
            for i in logs:
                if i.startswith("-"):
                    i = i[1:]
                if os.path.isfile(i):
                    self.add_copy_spec_limit(i, sizelimit=self.limit)

    def postproc(self):
        self.do_path_regex_sub(
            r"/etc/rsyslog*",
            r"ActionLibdbiPassword (.*)",
            r"ActionLibdbiPassword [********]"
        )
        self.do_path_regex_sub(
            r"/etc/rsyslog*",
            r"pwd=.*",
            r"pwd=[******]"
        )


class RedHatLogs(Logs, RedHatPlugin):

    option_list = [
        ("log_days", "the number of days logs to collect", "", 3)
    ]

    def setup(self):
        super(RedHatLogs, self).setup()
        messages = "/var/log/messages"
        self.add_copy_spec_limit("/var/log/secure*", sizelimit=self.limit)
        self.add_copy_spec_limit(messages + "*", sizelimit=self.limit)
        # collect three days worth of logs by default if the system is
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
        if not self.get_option("all_logs"):
            limit = self.get_option("log_size")
            self.add_copy_spec_limit("/var/log/syslog", sizelimit=limit)
            self.add_copy_spec_limit("/var/log/syslog.1", sizelimit=limit)
            self.add_copy_spec_limit("/var/log/kern.log", sizelimit=limit)
            self.add_copy_spec_limit("/var/log/kern.log.1", sizelimit=limit)
            self.add_copy_spec_limit("/var/log/udev", sizelimit=limit)
            self.add_copy_spec_limit("/var/log/dist-upgrade", sizelimit=limit)
            self.add_copy_spec_limit("/var/log/installer", sizelimit=limit)
            self.add_copy_spec_limit("/var/log/unattended-upgrades",
                                     sizelimit=limit)
            self.add_cmd_output('ls -alRh /var/log/')
        else:
            self.add_copy_spec("/var/log/")

# vim: set et ts=4 sw=4 :
