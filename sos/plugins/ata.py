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
import os


class Ata(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """ ATA and IDE information
    """

    plugin_name = "ata"
    profiles = ('storage', 'hardware')

    packages = ('hdparm', 'smartmontools')

    def setup(self):
        dev_path = '/dev'
        sys_block = '/sys/block'
        self.add_copy_spec('/proc/ide')
        if os.path.isdir(sys_block):
            for disk in os.listdir(sys_block):
                if disk.startswith("sd") or disk.startswith("hd"):
                    disk_path = os.path.join(dev_path, disk)
                    self.add_cmd_output([
                        "hdparm %s" % disk_path,
                        "smartctl -a %s" % disk_path
                    ])


# vim: set et ts=4 sw=4 :
