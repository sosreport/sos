# Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Systemd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ System management daemon
    """

    plugin_name = "systemd"
    profiles = ('system', 'services', 'boot')

    packages = ('systemd',)
    files = ('/usr/lib/systemd/systemd',)

    def setup(self):
        self.add_cmd_output([
            "systemctl show --all",
            "systemctl list-units",
            "systemctl list-units --failed",
            "systemctl list-units --all",
            "systemctl list-unit-files",
            "systemctl show-environment",
            "systemd-delta",
            "journalctl --list-boots",
            "ls -l /lib/systemd",
            "ls -l /lib/systemd/system-shutdown",
            "ls -l /lib/systemd/system-generators",
            "ls -l /lib/systemd/user-generators",
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
