# Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, SoSPredicate
from sos.utilities import is_executable


class Systemd(Plugin, IndependentPlugin):
    short_desc = 'System management daemon'

    plugin_name = "systemd"
    profiles = ('system', 'services', 'boot')

    packages = ('systemd',)
    files = ('/run/systemd/system',)

    def setup(self):

        self.add_file_tags({
            '/etc/systemd/journald.conf.*': 'insights_etc_journald_conf',
            '/usr/lib/systemd/journald.conf.*': 'insights_usr_journald_conf_d',
            '/etc/systemd/system.conf': 'insights_systemd_system_conf',
            '/etc/systemd/logind.conf': 'insights_systemd_logind_conf'
        })

        self.add_cmd_output([
            "systemctl status --all",
            "systemctl show --all",
            "systemctl show *service --all",
            # It is possible to do systemctl show with target, slice,
            # device, socket, scope, and mount too but service and
            # status --all mostly seems to cover the others.
            "systemctl list-units",
            "systemctl list-units --failed",
            "systemctl list-unit-files",
            "systemctl list-jobs",
            "systemctl list-dependencies",
            "systemctl list-timers --all",
            "systemctl list-machines",
            "systemctl show-environment",
            "systemd-delta",
            "systemd-analyze",
            "systemd-analyze blame",
            "systemd-analyze dump",
            "systemd-inhibit --list",
            "journalctl --list-boots",
            "ls -lR /lib/systemd",
            "timedatectl"
        ])

        # resolvectl command starts systemd-resolved service if that
        # is not running, so gate the commands by this predicate
        if is_executable('resolvectl'):
            resolvectl_status = 'resolvectl status'
            resolvectl_statistics = 'resolvectl statistics'
        else:
            resolvectl_status = 'systemd-resolve --status'
            resolvectl_statistics = 'systemd-resolve --statistics'
        self.add_cmd_output([
            resolvectl_status,
            resolvectl_statistics,
        ], pred=SoSPredicate(self, services=["systemd-resolved"]))

        self.add_cmd_output("systemd-analyze plot",
                            suggest_filename="systemd-analyze_plot.svg")

        if self.get_option("verify"):
            self.add_cmd_output("journalctl --verify")

        self.add_copy_spec([
            "/etc/systemd",
            "/lib/systemd/system",
            "/lib/systemd/user",
            "/etc/vconsole.conf",
            "/run/systemd/generator*",
            "/run/systemd/seats",
            "/run/systemd/sessions",
            "/run/systemd/system",
            "/run/systemd/users",
            "/etc/modules-load.d/*.conf",
            "/etc/yum/protected.d/systemd.conf",
            "/etc/tmpfiles.d/*.conf",
            "/run/tmpfiles.d/*.conf",
            "/usr/lib/tmpfiles.d/*.conf",
        ])
        self.add_forbidden_path('/dev/null')

# vim: set et ts=4 sw=4 :
