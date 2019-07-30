# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import platform
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class KDump(Plugin):
    """Kdump crash dumps
    """

    plugin_name = "kdump"
    profiles = ('system', 'debug')

    def setup(self):
        self.add_copy_spec([
            "/proc/cmdline"
        ])


class RedHatKDump(KDump, RedHatPlugin):

    files = ('/etc/kdump.conf',)
    packages = ('kexec-tools',)

    def setup(self):
        initramfs_img = "/boot/initramfs-" + platform.release() \
                        + "kdump.img"

        self.add_copy_spec([
            "/etc/kdump.conf",
            "/etc/udev/rules.d/*kexec.rules",
            "/var/crash/*/vmcore-dmesg.txt"
        ])

        if os.path.exists(initramfs_img):
            self.add_cmd_output("lsinitrd %s" % initramfs_img)


class DebianKDump(KDump, DebianPlugin, UbuntuPlugin):

    files = ('/etc/default/kdump-tools',)
    packages = ('kdump-tools',)

    def setup(self):
        initramfs_img = "/var/lib/kdump/initrd.img-" + platform.release()

        self.add_copy_spec([
            "/etc/default/kdump-tools"
        ])

        if os.path.exists(initramfs_img):
            self.add_cmd_output("lsinitrd %s" % initramfs_img)

# vim: set et ts=4 sw=4 :
