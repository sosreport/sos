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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from distutils.spawn import find_executable


class Lstopo(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """lstopo / machine topology/numa node information
    """

    plugin_name = "lstopo"
    profiles = ("system", "hardware")
    packages = ("hwloc-libs", )

    def setup(self):
        # binary depends on particular package, both require hwloc-libs one
        # hwloc-gui provides lstopo command
        # hwloc provides lstopo-no-graphics command
        if find_executable("lstopo"):
            cmd = "lstopo"
        else:
            cmd = "lstopo-no-graphics"
        self.add_cmd_output("%s --whole-io --of console" % cmd,
                            suggest_filename="lstopo.txt")
        self.add_cmd_output("%s --whole-io --of xml" % cmd,
                            suggest_filename="lstopo.xml")
