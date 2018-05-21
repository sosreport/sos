# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
