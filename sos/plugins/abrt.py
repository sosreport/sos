# Copyright (C) 2010 Red Hat, Inc., Tomas Smetana <tsmetana@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin


class Abrt(Plugin, RedHatPlugin):
    """Automatic Bug Reporting Tool
    """

    plugin_name = "abrt"
    profiles = ('system', 'debug')
    packages = ('abrt-cli', 'abrt-gui', 'abrt')
    files = ('/var/spool/abrt',)

    option_list = [
        ("detailed", 'collect detailed info for every report', 'slow', False)
    ]

    def info_detailed(self, list_file):
        for line in open(list_file).read().splitlines():
            if line.startswith("Directory:"):
                self.add_cmd_output("abrt-cli info -d '%s'" % line.split()[1])

    def setup(self):
        self.add_cmd_output("abrt-cli status")
        list_file = self.get_cmd_output_now("abrt-cli list")
        if self.get_option('detailed') and list_file:
            self.info_detailed(list_file)

# vim: set et ts=4 sw=4 :
