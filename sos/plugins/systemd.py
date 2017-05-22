# Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

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
            "systemctl show-environment",
            "systemd-delta",
            "systemd-analyze",
            "journalctl --list-boots",
            "ls -lR /lib/systemd",
            "timedatectl"
        ])

        if self.get_option("verify"):
            self.add_cmd_output("journalctl --verify")

        self.add_copy_spec([
            "/etc/systemd",
            "/lib/systemd/system",
            "/lib/systemd/user",
            "/etc/vconsole.conf",
            "/etc/yum/protected.d/systemd.conf"
        ])

# vim: set et ts=4 sw=4 :
