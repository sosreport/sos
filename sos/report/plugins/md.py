# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Md(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """MD RAID subsystem
    """

    plugin_name = 'md'
    profiles = ('storage',)

    def setup(self):
        self.add_cmd_output("mdadm -D /dev/md*")
        self.add_copy_spec([
            "/proc/mdstat",
            "/etc/mdadm.conf",
            "/dev/md/md-device-map",
            "/proc/sys/dev/raid/*",
            "/sys/block/md*/md*"
        ])


# vim: set et ts=4 sw=4 :
