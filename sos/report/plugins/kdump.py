# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import platform
from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class KDump(Plugin):

    short_desc = 'Kdump crash dumps'

    plugin_name = "kdump"
    profiles = ('system', 'debug')

    def setup(self):
        self.add_copy_spec([
            "/proc/cmdline",
            "/etc/sysconfig/kdump",
            "/proc/sys/kernel/panic",
            "/proc/sys/kernel/panic_on_oops",
            "/sys/kernel/kexec_loaded",
            "/sys/kernel/fadump_enabled",
            "/sys/kernel/fadump/enabled",
            "/sys/kernel/fadump_registered",
            "/sys/kernel/fadump/registered",
            "/sys/kernel/fadump/mem_reserved",
            "/sys/kernel/kexec_crash_loaded",
            "/sys/kernel/kexec_crash_size"
        ])


class RedHatKDump(KDump, RedHatPlugin):

    files = ('/etc/kdump.conf',)
    packages = ('kexec-tools',)

    def fstab_parse_fs(self, device):
        with open(self.path_join('/etc/fstab'), 'r') as fp:
            for line in fp:
                if line.startswith((device)):
                    return line.split()[1].rstrip('/')
        return ""

    def read_kdump_conffile(self):
        fs = ""
        path = "/var/crash"

        with open(self.path_join('/etc/kdump.conf'), 'r') as fp:
            for line in fp:
                if line.startswith("path"):
                    path = line.split()[1]
                elif line.startswith(("ext2", "ext3", "ext4", "xfs")):
                    device = line.split()[1]
                    fs = self.fstab_parse_fs(device)
        return fs + path

    def setup(self):
        super(RedHatKDump, self).setup()

        initramfs_img = "/boot/initramfs-" + platform.release() \
                        + "kdump.img"
        if self.path_exists(initramfs_img):
            self.add_cmd_output("lsinitrd %s" % initramfs_img)

        self.add_copy_spec([
            "/etc/kdump.conf",
            "/etc/udev/rules.d/*kexec.rules",
            "/var/crash/*/vmcore-dmesg.txt",
            "/var/crash/*/kexec-dmesg.log",
            "/var/log/kdump.log"
        ])
        try:
            path = self.read_kdump_conffile()
        except Exception:
            # set no filesystem and default path
            path = "/var/crash"

        self.add_copy_spec("{}/*/vmcore-dmesg.txt".format(path))
        self.add_copy_spec("{}/*/kexec-dmesg.log".format(path))


class DebianKDump(KDump, DebianPlugin, UbuntuPlugin):

    files = ('/etc/default/kdump-tools',)
    packages = ('kdump-tools',)

    def setup(self):
        super(DebianKDump, self).setup()

        initramfs_img = "/var/lib/kdump/initrd.img-" + platform.release()
        if self.path_exists(initramfs_img):
            self.add_cmd_output("lsinitramfs -l %s" % initramfs_img)

        self.add_cmd_output("kdump-config show")

        self.add_copy_spec([
            "/etc/default/kdump-tools"
        ])

# vim: set et ts=4 sw=4 :
