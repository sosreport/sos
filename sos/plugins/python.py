# Copyright (C) 2014 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Python(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Python_Version information.
    """

    plugin_name = 'python'

    packages = ('python',)

    def setup(self):
        self.add_cmd_output("python -V", suggest_filename="python-version")

# vim: et ts=4 sw=4
