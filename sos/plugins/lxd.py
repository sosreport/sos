# Copyright (C) 2016 Jorge Niedbalski <niedbalski@ubuntu.com>
#
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

from sos.plugins import Plugin, UbuntuPlugin


class LXD(Plugin, UbuntuPlugin):
    """LXD is a containers hypervisor.
    """
    plugin_name = 'lxd'

    def setup(self):
        self.add_copy_spec([
            "/var/lib/lxd/lxd.db",
            "/etc/default/lxc-bridge",
        ])

        self.add_copy_spec("/var/log/lxd*",
                           sizelimit=self.get_option("log_size"))

        # List of containers available on the machine
        self.add_cmd_output([
            "lxc list",
            "lxc profile list",
            "lxc image list",
        ])

        self.add_cmd_output([
            "find /var/lib/lxd -maxdepth 2 -type d -ls",
        ], suggest_filename='var-lxd-dirs.txt')

# vim: set et ts=4 sw=4 :
