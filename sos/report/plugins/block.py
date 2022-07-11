# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Block(Plugin, IndependentPlugin):

    short_desc = 'Block device information'

    plugin_name = 'block'
    profiles = ('storage', 'hardware')
    verify_packages = ('util-linux',)
    files = ('/sys/block',)

    def setup(self):
        self.add_forbidden_path("/sys/block/*/queue/iosched")

        self.add_file_tags({
            '/sys/block/.*/queue/scheduler': 'scheduler'
        })

        self.add_cmd_output([
            "lsblk",
            "lsblk -t",
            "lsblk -D",
            "blkid -c /dev/null",
            "blockdev --report",
            "ls -lanR /dev",
            "ls -lanR /sys/block",
            "lsblk -O -P",
            "losetup -a",
        ])

        # legacy location for non-/run distributions
        self.add_copy_spec([
            "/etc/blkid.tab",
            "/run/blkid/blkid.tab",
            "/proc/partitions",
            "/proc/diskstats",
            "/sys/block/*/queue/",
            "/sys/block/sd*/device/timeout",
            "/sys/block/hd*/device/timeout",
            "/sys/block/sd*/device/state",
            "/sys/block/loop*/loop/",
        ])

        cmds = [
            "parted -s %(dev)s unit s print",
            "fdisk -l %(dev)s",
            "udevadm info %(dev)s",
            "udevadm info -a %(dev)s"
        ]
        self.add_device_cmd(cmds, devices='block', blacklist='ram.*')

        lsblk = self.collect_cmd_output("lsblk -f -a -l")
        # for LUKS devices, collect cryptsetup luksDump
        if lsblk['status'] == 0:
            for line in lsblk['output'].splitlines():
                if 'crypto_LUKS' in line:
                    dev = line.split()[0]
                    self.add_cmd_output('cryptsetup luksDump /dev/%s' % dev)

# vim: set et ts=4 sw=4 :
