# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Block(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Block device information
    """

    plugin_name = 'block'
    profiles = ('storage', 'hardware')
    verify_packages = ('util-linux',)
    files = ('/sys/block',)

    def setup(self):
        self.add_cmd_output([
            "lsblk",
            "lsblk -t",
            "lsblk -D",
            "blkid -c /dev/null",
            "blockdev --report",
            "ls -lanR /dev",
            "ls -lanR /sys/block"
        ])

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
                if disk.startswith("ram"):
                    continue
                disk_path = os.path.join('/dev/', disk)
                self.add_udev_info(disk_path)
                self.add_udev_info(disk_path, attrs=True)
                self.add_cmd_output([
                    "parted -s %s unit s print" % (disk_path),
                    "fdisk -l %s" % disk_path
                ])

# vim: set et ts=4 sw=4 :
