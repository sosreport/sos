# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Md(Plugin, IndependentPlugin):

    short_desc = 'MD RAID subsystem'

    plugin_name = 'md'
    profiles = ('storage',)

    def setup(self):
        self.add_cmd_output("mdadm -D /dev/md*")
        self.add_blockdev_cmd("mdadm -E %(dev)s",
                              blacklist=['ram.*', 'zram.*'])
        self.add_copy_spec([
            "/etc/mdadm.conf",
            "/dev/md/md-device-map",
            "/proc/sys/dev/raid/*",
            "/sys/block/md*/md*"
        ])

        self.add_copy_spec("/proc/mdstat", tags='mdstat')

# vim: set et ts=4 sw=4 :
