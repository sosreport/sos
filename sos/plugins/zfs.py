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


from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Zfs(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """ZFS filesystem
    """

    plugin_name = 'zfs'
    profiles = ('storage',)

    packages = ('zfsutils-linux', 'zfs',)

    def setup(self):
        self.add_cmd_output([
            "zfs get all",
            "zfs list -t all -o space",
            "zpool list",
            "zpool status -vx"
        ])

        zpools = self.call_ext_prog("zpool list -H -o name")
        if zpools['status'] == 0:
            zpools_list = zpools['output'].splitlines()
            for zpool in zpools_list:
                self.add_cmd_output("zpool get all %s" % zpool)

# vim: set et ts=4 sw=4 :
