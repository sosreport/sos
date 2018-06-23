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

        self.add_copy_spec("/var/log/boot.log")
        self.add_copy_spec("/var/log/cloud-init*")
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
            logs += self.do_regex_find_all(r"^\S+\s+(-?\/.*$)\s+", config)

        for i in logs:
            if i.startswith("-"):
                i = i[1:]
            if os.path.isfile(i):
                self.add_copy_spec(i)

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
        # NOTE: for historical reasons the 'messages' and 'secure' log
        # paths for the RedHatLogs plugin do not obey the normal --all-logs
        # convention. The rotated copies are collected unconditionally
        # due to their frequent importance in diagnosing problems.
        messages = "/var/log/messages"
        secure = "/var/log/secure"

        have_messages = os.path.exists(messages)

        self.add_copy_spec(secure + "*")
        self.add_copy_spec(messages + "*")

        # collect three days worth of logs by default if the system is
        # configured to use the journal and not /var/log/messages
        if not have_messages and self.is_installed("systemd"):
            try:
                days = int(self.get_option("log_days"))
            except ValueError:
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
            self.add_copy_spec([
                "/var/log/syslog",
                "/var/log/syslog.1",
                "/var/log/kern.log",
                "/var/log/kern.log.1",
                "/var/log/udev",
                "/var/log/dist-upgrade",
                "/var/log/installer",
                "/var/log/unattended-upgrades"
            ])
            self.add_cmd_output('ls -alRh /var/log/')
        else:
            self.add_copy_spec("/var/log/")

# vim: set et ts=4 sw=4 :
