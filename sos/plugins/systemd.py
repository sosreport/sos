# Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Systemd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ System management daemon
    """

    plugin_name = "systemd"
    profiles = ('system', 'services', 'boot')

    packages = ('systemd',)
    files = (
        '/usr/lib/systemd/systemd',
        '/lib/systemd/systemd'
    )

    def setup(self):
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
            "systemd-resolve --status",
            "systemd-resolve --statistics",
            "journalctl --list-boots",
            "ls -lR /lib/systemd",
            "timedatectl"
        ])

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
            "/etc/yum/protected.d/systemd.conf"
        ])
        self.add_forbidden_path('/dev/null')

# vim: set et ts=4 sw=4 :
