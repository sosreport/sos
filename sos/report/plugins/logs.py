# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import glob
from sos.report.plugins import Plugin, IndependentPlugin


class Logs(Plugin, IndependentPlugin):

    short_desc = 'System logs'

    plugin_name = "logs"
    profiles = ('system', 'hardware', 'storage')

    def setup(self):
        confs = ['/etc/syslog.conf', '/etc/rsyslog.conf']
        logs = []

        since = self.get_option("since")

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

        self.add_copy_spec([
            "/etc/syslog.conf",
            "/etc/rsyslog.conf",
            "/etc/rsyslog.d",
            "/var/log/boot.log",
            "/var/log/installer",
            "/var/log/messages*",
            "/var/log/secure*",
            "/var/log/udev",
            "/var/log/dist-upgrade",
        ])

        self.add_cmd_output("journalctl --disk-usage")
        self.add_cmd_output('ls -alRh /var/log/')

        # collect journal logs if:
        # - there is some data present, either persistent or runtime only
        # - systemd-journald service exists
        # otherwise fallback to collecting few well known logfiles directly
        journal = any([os.path.exists(p + "/log/journal/")
                      for p in ["/var", "/run"]])
        if journal and self.is_service("systemd-journald"):
            self.add_journal(since=since, tags='journal_full', priority=100)
            self.add_journal(boot="this", catalog=True, since=since,
                             tags='journal_since_boot')
            self.add_journal(boot="last", catalog=True, since=since,
                             tags='journal_last_boot')
            if self.get_option("all_logs"):
                self.add_copy_spec([
                    "/var/log/journal/*",
                    "/run/log/journal/*"
                ])
        else:  # If not using journal
            if not self.get_option("all_logs"):
                self.add_copy_spec([
                    "/var/log/syslog",
                    "/var/log/syslog.1",
                    "/var/log/syslog.2*",
                    "/var/log/kern.log",
                    "/var/log/kern.log.1",
                    "/var/log/kern.log.2*",
                    "/var/log/auth.log",
                    "/var/log/auth.log.1",
                    "/var/log/auth.log.2*",
                ])
            else:
                self.add_copy_spec([
                    "/var/log/syslog*",
                    "/var/log/kern.log*",
                    "/var/log/auth.log*",
                ])

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

# vim: set et ts=4 sw=4 :
