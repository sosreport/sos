## Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class systemd(Plugin, RedHatPlugin):
    """ Information on systemd and related subsystems
    """

    plugin_name = "systemd"

    packages = ('systemd',)
    files = ('/usr/lib/systemd/systemd',)

    def setup(self):
        self.add_cmd_output("systemctl show --all")
        self.add_cmd_output("systemctl list-units --failed")
        self.add_cmd_output("systemctl list-unit-files")
        self.add_cmd_output("systemctl list-units --all")
        self.add_cmd_output("systemctl dump")
        self.add_cmd_output("systemd-delta")
        self.add_cmd_output("journalctl --verify")
        self.add_cmd_output("journalctl --all --this-boot --no-pager")
        self.add_cmd_output("journalctl --all --this-boot --no-pager -o verbose")
        self.add_cmd_output("ls -l /lib/systemd")
        self.add_cmd_output("ls -l /lib/systemd/system-shutdown")
        self.add_cmd_output("ls -l /lib/systemd/system-generators")
        self.add_cmd_output("ls -l /lib/systemd/user-generators")

        self.add_copy_specs(["/etc/systemd",
                           "/lib/systemd/system",
                           "/lib/systemd/user",
                           "/etc/vconsole.conf",
                           "/etc/yum/protected.d/systemd.conf"])

