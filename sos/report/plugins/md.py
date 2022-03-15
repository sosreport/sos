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
        mdadm_members = self.exec_cmd("lsblk -o NAME,FSTYPE -r")
        if mdadm_members['status'] == 0:
            for line in mdadm_members['output'].splitlines():
                if 'linux_raid_member' in line:
                    dev = line.split()[0]
                    self.add_cmd_output('mdadm -E /dev/%s' % dev)

        self.add_copy_spec([
            "/etc/mdadm.conf",
            "/dev/md/md-device-map",
            "/proc/sys/dev/raid/*",
            "/sys/block/md*/md*"
        ])

        self.add_copy_spec("/proc/mdstat", tags='mdstat')

# vim: set et ts=4 sw=4 :
