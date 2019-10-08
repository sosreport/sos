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


class Logs(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """System logs"""

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
            "/var/log/unattended-upgrades",
            "/var/log/messages*",
            "/var/log/secure*",
            "/var/log/udev",
            "/var/log/dist-upgrade",
        ])

        self.add_cmd_output("journalctl --disk-usage")
        self.add_cmd_output('ls -alRh /var/log/')

        journal = os.path.exists("/var/log/journal/")
        if journal and self.is_installed("systemd"):
            self.add_journal(since=since)
            self.add_journal(boot="this", catalog=True)
            self.add_journal(boot="last", catalog=True)
            if self.get_option("all_logs"):
                self.add_copy_spec("/var/log/journal/*")
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
