# Copyright (C) 2015 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

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


class TargetCli(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """TargetCLI TCM/LIO configuration
    """
    packages = ('targetcli', 'python-rtslib')
    profiles = ('storage', )
    plugin_name = 'targetcli'

    def setup(self):
        self.add_cmd_output([
            "targetcli ls",
            "targetcli status",
            "journalctl -u target",
            "systemctl status target.service"
        ])
        self.add_copy_spec("/etc/target")

# vim: set et ts=4 sw=4 :
