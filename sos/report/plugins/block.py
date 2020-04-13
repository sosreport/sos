# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Block(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Block device information
    """

    plugin_name = 'block'
    profiles = ('storage', 'hardware')
    verify_packages = ('util-linux',)
    files = ('/sys/block',)

    def setup(self):
        self.add_forbidden_path("/sys/block/*/queue/iosched")

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
            "/sys/block/*/queue/"
        ])

        cmds = [
            "parted -s %(dev)s unit s print",
            "fdisk -l %(dev)s",
            "udevadm info %(dev)s",
            "udevadm info -a %(dev)s"
        ]
        self.add_blockdev_cmd(cmds, blacklist='ram.*')

        lsblk = self.collect_cmd_output("lsblk -f -a -l")
        # for LUKS devices, collect cryptsetup luksDump
        if lsblk['status'] == 0:
            for line in lsblk['output'].splitlines():
                if 'crypto LUKS' in line:
                    dev = line.split()[0]
                    self.add_cmd_output('cryptsetup luksDump /dev/%s' % dev)

# vim: set et ts=4 sw=4 :
