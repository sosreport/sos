# Copyright (C) 2013 Louis Bouchard <louis.bouchard@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, UbuntuPlugin, DebianPlugin


class Apt(Plugin, DebianPlugin, UbuntuPlugin):
    """ Apt Plugin
    """

    plugin_name = 'apt'

    def setup(self):
        self.add_copy_specs([
            "/etc/apt", "/var/log/apt"
        ])

        shell_cmd = "sh -c '%s'" % (
            "dpkg -l | grep ^ii |"
            "cut -d \" \" -f3 |"
            "xargs apt-cache policy"
            )
        self.add_cmd_outputs([
            "apt-get check",
            "apt-config dump",
            "apt-cache stats",
            "apt-cache policy",
            shell_cmd
        ])

# vim: et ts=4 sw=4
