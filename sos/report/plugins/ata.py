# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
