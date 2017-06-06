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

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Block(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Block device information
    """

    plugin_name = 'block'
    profiles = ('storage', 'hardware')
    option_list = [("all", "get all block info", "fast", False)]

    def get_info_for_all_devices(self):
        block_devices = [blk for blk in os.listdir('/sys/block/')]
        for blk in block_devices:
            all_files = self.call_ext_prog("find /sys/block/%s/ -type f" % blk)
            if all_files['status'] == 0:
                files = all_files['output'].splitlines()
                self.add_copy_spec(files)

    def setup(self):
        self.add_cmd_output([
            "lsblk",
            "blkid -c /dev/null",
            "blockdev --report",
            "ls -lanR /dev",
            "ls -lanR /sys/block"
        ])

        if self.get_option("all"):
            self.get_info_for_all_devices()

        # legacy location for non-/run distributions
        self.add_copy_spec([
            "/etc/blkid.tab",
            "/run/blkid/blkid.tab",
            "/proc/partitions",
            "/proc/diskstats",
            "/sys/block/*/queue/scheduler"
        ])

        if os.path.isdir("/sys/block"):
            for disk in os.listdir("/sys/block"):
                if disk in [".",  ".."] or disk.startswith("ram"):
                    continue
                disk_path = os.path.join('/dev/', disk)
                self.add_cmd_output([
                    "udevadm info -ap /sys/block/%s" % (disk),
                    "parted -s %s unit s print" % (disk_path),
                    "fdisk -l %s" % disk_path
                ])

# vim: set et ts=4 sw=4 :
