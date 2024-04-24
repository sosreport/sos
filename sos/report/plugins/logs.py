# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import glob
from sos.report.plugins import Plugin, PluginOpt, IndependentPlugin, CosPlugin


class LogsBase(Plugin):

    short_desc = 'System logs'

    plugin_name = "logs"
    profiles = ('system', 'hardware', 'storage')

    def setup(self):
        rsyslog = 'etc/rsyslog.conf'
        confs = ['/etc/syslog.conf', rsyslog]
        logs = []

        if self.path_exists(rsyslog):
            with open(self.path_join(rsyslog), 'r', encoding='UTF-8') as conf:
                for line in conf.readlines():
                    if line.startswith('$IncludeConfig'):
                        confs += glob.glob(line.split()[1])

        for conf in confs:
            if not self.path_exists(self.path_join(conf)):
                continue
            config = self.path_join(conf)
            logs += self.do_regex_find_all(r"^\S+\s+(-?\/.*$)\s+", config)

        for i in logs:
            if i.startswith("-"):
                i = i[1:]
            if self.path_isfile(i):
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
            "/var/log/auth.log",
        ])

        self.add_cmd_output("journalctl --disk-usage")
        self.add_cmd_output('ls -alRh /var/log/')

        # collect journal logs if:
        # - there is some data present, either persistent or runtime only
        # - systemd-journald service exists
        # otherwise fallback to collecting few well known logfiles directly
        journal = any(self.path_exists(self.path_join(p, "log/journal/"))
                      for p in ["/var", "/run"])
        if journal and self.is_service("systemd-journald"):
            self.add_journal(tags=['journal_full', 'journal_all'],
                             priority=100)
            self.add_journal(boot="this", tags='journal_since_boot')
            self.add_journal(boot="last", tags='journal_last_boot')
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
            r"(ActionLibdbiPassword |pwd=)(.*)",
            r"\1[********]"
        )


class IndependentLogs(LogsBase, IndependentPlugin):
    """
    This plugin will collect logs traditionally considered to be "system" logs,
    meaning those such as /var/log/messages, rsyslog, and journals that are
    not limited to unit-specific entries.

    Note that the --since option will apply to journal collections by this
    plugin as well as the typical application to log files. Most users can
    expect typical journal collections to include the "full" journal, as well
    as journals limited to this boot and the previous boot.
    """

    plugin_name = "logs"
    profiles = ('system', 'hardware', 'storage')


class CosLogs(LogsBase, CosPlugin):
    option_list = [
        PluginOpt(name="log_days", default=3,
                  desc="the number of days logs to collect")
    ]

    def setup(self):
        super().setup()
        if self.get_option("all_logs"):
            self.add_cmd_output("journalctl -o export")
        else:
            days = self.get_option("log_days", 3)
            self.add_journal(since=f"-{days}days")

# vim: set et ts=4 sw=4 :
