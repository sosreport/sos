# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

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
from sos.utilities import is_executable


class Alternatives(Plugin, RedHatPlugin):
    """System alternatives
    """

    def check_enabled(self):
        return is_executable('alternatives')

    def setup(self):
        self.add_cmd_output([
            'alternatives --list',
            'alternatives --version'
        ])

        alts = []
        ignore = [
            'cdrecord',
            'ld',
            'mkisofs',
            'whois',
            'xinputrc'
        ]

        res = self.get_command_output('alternatives --list')
        if res['status'] == 0:
            for line in res['output'].splitlines():
                alt = line.split()[0]
                if alt not in ignore:
                    alts.append(alt)

            for alt in alts:
                self.add_cmd_output("alternatives --display %s" % alt)
