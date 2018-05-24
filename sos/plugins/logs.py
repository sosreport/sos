# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import glob
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

        self.limit = (None if self.get_option("all_logs")
                      else self.get_option("log_size"))
        self.add_copy_spec("/var/log/boot.log", sizelimit=self.limit)
        self.add_copy_spec("/var/log/cloud-init*", sizelimit=self.limit)
        self.add_journal(boot="this", catalog=True)
        self.add_journal(boot="last", catalog=True)
        self.add_cmd_output("journalctl --disk-usage")

        confs = ['/etc/syslog.conf', '/etc/rsyslog.conf']
        logs = []

        if os.path.exists('/etc/rsyslog.conf'):
            with open('/etc/rsyslog.conf', 'r') as conf:
                for line in conf.readlines():
                    if line.startswith('$IncludeConfig'):
                        confs += glob.glob(line.split()[1])

        for conf in confs:
            if not os.path.exists(conf):
                continue
            config = self.join_sysroot(conf)
            logs += self.do_regex_find_all("^\S+\s+(-?\/.*$)\s+", config)

        for i in logs:
            if i.startswith("-"):
                i = i[1:]
            if os.path.isfile(i):
                self.add_copy_spec(i, sizelimit=self.limit)

        if self.get_option('all_logs'):
            self.add_journal(boot="this", allfields=True, output="verbose")
            self.add_journal(boot="last", allfields=True, output="verbose")

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
        secure = "/var/log/secure"

        if self.get_option("all_logs"):
            messages += "*"
            secure += "*"

        self.add_copy_spec(secure, sizelimit=self.limit)
        self.add_copy_spec(messages, sizelimit=self.limit)

        # collect three days worth of logs by default if the system is
        # configured to use the journal and not /var/log/messages
        if not os.path.exists(messages) and self.is_installed("systemd"):
            try:
                days = int(self.get_option("log_days"))
            except:
                days = 3
            if self.get_option("all_logs"):
                since = ""
            else:
                since = "-%ddays" % days
            self.add_journal(since=since)


class DebianLogs(Logs, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianLogs, self).setup()
        if not self.get_option("all_logs"):
            self.add_copy_spec("/var/log/syslog", sizelimit=self.limit)
            self.add_copy_spec("/var/log/syslog.1", sizelimit=self.limit)
            self.add_copy_spec("/var/log/kern.log", sizelimit=self.limit)
            self.add_copy_spec("/var/log/kern.log.1", sizelimit=self.limit)
            self.add_copy_spec("/var/log/udev", sizelimit=self.limit)
            self.add_copy_spec("/var/log/dist-upgrade", sizelimit=self.limit)
            self.add_copy_spec("/var/log/installer", sizelimit=self.limit)
            self.add_copy_spec("/var/log/unattended-upgrades",
                               sizelimit=self.limit)
            self.add_cmd_output('ls -alRh /var/log/')
        else:
            self.add_copy_spec("/var/log/")

# vim: set et ts=4 sw=4 :
