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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Dmraid(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """dmraid software RAID
    """

    plugin_name = 'dmraid'
    profiles = ('hardware', 'storage')
    option_list = [
        ("metadata", "capture dmraid device metadata", "slow", False)
    ]

    # V - {-V/--version}
    # b - {-b|--block_devices}
    # r - {-r|--raid_devices}
    # s - {-s|--sets}
    # t - [-t|--test]
    # a - {-a|--activate} {y|n|yes|no}
    # D - [-D|--dump_metadata]
    dmraid_options = ['V', 'b', 'r', 's', 'tay']

    def setup(self):
        for opt in self.dmraid_options:
            self.add_cmd_output("dmraid -%s" % (opt,))
        if self.get_option("metadata"):
            metadata_path = self.get_cmd_output_path("metadata")
            self.add_cmd_output("dmraid -rD", runat=metadata_path,
                                chroot=self.tmp_in_sysroot())

# vim: set et ts=4 sw=4 :
