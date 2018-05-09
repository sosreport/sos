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
from glob import glob


class Boot(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Bootloader information
    """

    plugin_name = 'boot'
    profiles = ('system', 'boot')
    packages = ('grub', 'grub2', 'grub-common', 'grub2-common', 'zipl')

    option_list = [
        ("all-images", "collect lsinitrd for all images", "slow", False)
    ]

    def setup(self):
        self.add_copy_spec([
            # legacy / special purpose bootloader configs
            "/etc/milo.conf",
            "/etc/silo.conf",
            "/boot/efi/efi/redhat/elilo.conf",
            "/etc/yaboot.conf",
            "/boot/yaboot.conf"
        ])
        self.add_cmd_output([
            "ls -lanR /boot",
            "lsinitrd"
        ])

        self.add_cmd_output("efibootmgr -v")

        if self.get_option("all-images"):
            for image in glob('/boot/initr*.img'):
                if image[-9:] == "kdump.img":
                    continue
                self.add_cmd_output("lsinitrd %s" % image)


# vim: set et ts=4 sw=4 :
