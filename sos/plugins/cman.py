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
import re
from glob import glob


class Cman(Plugin, RedHatPlugin):
    """cman based Red Hat Cluster High Availability
    """

    plugin_name = "cman"
    profiles = ("cluster",)

    packages = [
        "luci",
        "cman",
        "clusterlib",
    ]

    files = ["/etc/cluster/cluster.conf"]

    debugfs_path = "/sys/kernel/debug"
    _debugfs_cleanup = False

    def setup(self):

        self.add_copy_spec([
            "/etc/cluster.conf",
            "/etc/cluster",
            "/etc/sysconfig/cluster",
            "/etc/sysconfig/cman",
            "/var/log/cluster",
            "/etc/fence_virt.conf",
            "/var/lib/luci/data/luci.db",
            "/var/lib/luci/etc",
            "/var/log/luci"
        ])

        self.add_cmd_output([
            "cman_tool services",
            "cman_tool nodes",
            "cman_tool status",
            "ccs_tool lsnode",
            "mkqdisk -L",
            "group_tool dump",
            "fence_tool dump",
            "fence_tool ls -n",
            "clustat",
            "rg_test test /etc/cluster/cluster.conf"
        ])

    def postproc(self):
        for cluster_conf in glob("/etc/cluster/cluster.conf*"):
            self.do_file_sub(
                cluster_conf,
                r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")",
                r"\1%s" % ('"***"')
            )

        self.do_path_regex_sub(
            "/var/lib/luci/etc/.*\.ini",
            r"(.*secret\s*=\s*)\S+",
            r"\1******"
        )
        return

# vim: et ts=4 sw=4
