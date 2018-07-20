# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from os.path import exists, isdir, isfile, join
from os import listdir
from glob import glob

RSYSLOG_D = "/etc/rsyslog.d"
SYSLOG_CONF = "/etc/syslog.conf"
RSYSLOG_CONF = "/etc/rsyslog.conf"


class Logs(Plugin):
    """System logs"""

    plugin_name = "logs"
    profiles = ('system', 'hardware', 'storage')

    option_list = [
        ("nojournal", "Disable collection of journal data", "", False),
        ("log_days", "the number of days of journal logs to collect", "", 3)
    ]

    def setup(self):
        self.add_copy_spec([
            SYSLOG_CONF,
            RSYSLOG_CONF,
            RSYSLOG_D
        ])

        self.add_copy_spec("/var/log/boot.log")
        self.add_copy_spec("/var/log/cloud-init*")

        if not self.get_option("nojournal"):
            self.add_journal(boot="this", catalog=True)
            self.add_journal(boot="last", catalog=True)
            self.add_cmd_output("journalctl --disk-usage")

        confs = [SYSLOG_CONF, RSYSLOG_CONF]
        logs = []

        def is_cfg(path):
            return path.endswith(".conf")

        def get_conf_paths(path):
            # Need to handle the three allowed styles of config specification:
            # * config file path
            # * path to a directory containing configuration files
            # * glob specifying particular files in a directory
            if isfile(path):
                return [path]
            if isdir(path):
                return [join(RSYSLOG_D, f) for f in listdir(path) if is_cfg(f)]
            if "*" in path:
                return glob(path)

        if exists(RSYSLOG_D):
            confs += get_conf_paths(RSYSLOG_D)

        if exists(RSYSLOG_CONF):
            with open(RSYSLOG_CONF, 'r') as conf:
                for line in conf.readlines():
                    if line.startswith('$IncludeConfig'):
                        name, path = line.split()
                        confs += get_conf_paths(path)

        for conf in confs:
            if not exists(conf):
                continue
            config = self.join_sysroot(conf)
            logs += self.do_regex_find_all(r"^\S+\s+(-?\/.*$)\s+", config)

        for i in logs:
            if i.startswith("-"):
                i = i[1:]
            if isfile(i):
                self.add_copy_spec(i)

        if not self.get_option("nojournal") and self.get_option('all_logs'):
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
    def setup(self):
        super(RedHatLogs, self).setup()
        # NOTE: for historical reasons the 'messages' and 'secure' log
        # paths for the RedHatLogs plugin do not obey the normal --all-logs
        # convention. The rotated copies are collected unconditionally
        # due to their frequent importance in diagnosing problems.
        messages = "/var/log/messages"
        secure = "/var/log/secure"

        nojournal = self.get_option("nojournal")

        have_messages = exists(messages)
        use_journal = not (nojournal or have_messages)

        self.add_copy_spec(secure + "*")
        self.add_copy_spec(messages + "*")

        # collect three days worth of logs by default if the system is
        # configured to use the journal and not /var/log/messages
        if use_journal and self.is_installed("systemd"):
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
