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

    def get_luks_devices(self, lsblk_file):
        out = []
        try:
            lsblk_out = open(lsblk_file).read()
        except IOError:
            return out
        for line in lsblk_out.splitlines():
            # find in output lines like
            # sda2      crypto_LUKS    <uuid>
            # loop0     crypto_LUKS    <uuid>
            # and separate device name - it will be the 1st string on the line
            if 'crypto_LUKS' in line:
                dev = line.split()[0]
                out.append(dev)
        return out

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
                queue_path = os.path.join('/sys/block/', disk, 'queue')
                self.add_udev_info(disk_path)
                self.add_udev_info(disk_path, attrs=True)
                self.add_udev_info(queue_path, attrs=True)
                self.add_cmd_output([
                    "parted -s %s unit s print" % (disk_path),
                    "fdisk -l %s" % disk_path
                ])

        lsblk_file = self.get_cmd_output_now("lsblk -f -a -l")
        # for LUKS devices, collect cryptsetup luksDump
        if lsblk_file:
            for dev in self.get_luks_devices(lsblk_file):
                self.add_cmd_output('cryptsetup luksDump /dev/%s' % dev)

# vim: set et ts=4 sw=4 :
