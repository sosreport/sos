# Copyright (C) 2013 Red Hat, Inc., Lukas Zapletal <lzap@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin


class Foreman(Plugin, RedHatPlugin):
    """Foreman project related information
    """

    plugin_name = 'foreman'
    packages = ('foreman')

    def setup(self):
        cmd = "foreman-debug"
        path = self.get_cmd_output_path(name="foreman-debug")
        self.add_cmd_output("%s -q -a -d %s" % (cmd, path))

# vim: et ts=4 sw=4
