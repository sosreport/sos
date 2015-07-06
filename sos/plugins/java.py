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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Java(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """Java runtime"""

    plugin_name = "java"
    profiles = ('webserver', 'java')

    def setup(self):
        self.add_copy_spec("/etc/java")
        self.add_forbidden_path("/etc/java/security")
        self.add_cmd_output("alternatives --display java",
                            root_symlink="java")
        self.add_cmd_output("readlink -f /usr/bin/java")


# vim: set et ts=4 sw=4 :
