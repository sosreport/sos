# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Btrfs(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """Btrfs filesystem
    """

    plugin_name = 'btrfs'
    profiles = ('storage',)

    packages = ('btrfs-progs', 'btrfs-tools')

    def setup(self):
        self.add_cmd_output([
            "btrfs filesystem show",
            "btrfs version"
        ])

# vim: set et ts=4 sw=4 :
