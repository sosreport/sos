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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class systemd(Plugin, RedHatPlugin):
    """ Information on systemd and related subsystems
    """

    plugin_name = "systemd"

    packages = ('systemd',)
    files = ('/usr/lib/systemd/systemd',)

    def setup(self):
        self.addCmdOutput("systemctl show --all")
        self.addCmdOutput("systemctl list-units --failed")
        self.addCmdOutput("systemctl list-unit-files")
        self.addCmdOutput("systemctl list-units --all")
        self.addCmdOutput("systemctl dump")
        self.addCmdOutput("systemd-delta")
        self.addCmdOutput("journalctl --verify")
        self.addCmdOutput("journalctl --all --this-boot --no-pager")
        self.addCmdOutput("journalctl --all --this-boot --no-pager -o verbose")
        self.addCmdOutput("ls -l /lib/systemd")
        self.addCmdOutput("ls -l /lib/systemd/system-shutdown")
        self.addCmdOutput("ls -l /lib/systemd/system-generators")
        self.addCmdOutput("ls -l /lib/systemd/user-generators")

        self.addCopySpecs(["/etc/systemd",
                           "/lib/systemd/system",
                           "/lib/systemd/user",
                           "/etc/vconsole.conf",
                           "/etc/yum/protected.d/systemd.conf"])

