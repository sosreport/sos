# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import platform
from sos.report.plugins import (Plugin, PluginOpt, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, CosPlugin, AzurePlugin)


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
            "/sys/kernel/fadump",
            "/sys/kernel/fadump_enabled",
            "/sys/kernel/fadump_registered",
            "/sys/kernel/kexec_crash_size"
        ])

        self.add_copy_spec("/sys/kernel/kexec_crash_loaded",
                           tags="kexec_crash_loaded")


class RedHatKDump(KDump, RedHatPlugin):

    files = ('/etc/kdump.conf',)
    packages = ('kexec-tools',)

    option_list = [
        PluginOpt("get-vm-core", default=False, val_type=bool,
                  desc="collect vm core")
    ]

    def fstab_parse_fs(self, device):
        """ Parse /etc/fstab file """
        fstab = self.path_join('/etc/fstab')
        with open(fstab, 'r', encoding='UTF-8') as file:
            for line in file:
                if line.startswith((device)):
                    return line.split()[1].rstrip('/')
        return ""

    def read_kdump_conffile(self):
        """ Parse /etc/kdump file """
        fsys = ""
        path = "/var/crash"

        kdump = '/etc/kdump.conf'
        with open(kdump, 'r', encoding='UTF-8') as file:
            for line in file:
                if line.startswith("path"):
                    path = line.split()[1]
                elif line.startswith(("ext2", "ext3", "ext4", "xfs")):
                    device = line.split()[1]
                    fsys = self.fstab_parse_fs(device)
        return fsys + path

    def setup(self):
        super().setup()

        initramfs_img = "/boot/initramfs-" + platform.release() \
                        + "kdump.img"
        if self.path_exists(initramfs_img):
            self.add_cmd_output(f"lsinitrd {initramfs_img}")

        self.add_copy_spec([
            "/etc/kdump.conf",
            "/etc/udev/rules.d/*kexec.rules",
            "/usr/lib/udev/rules.d/*kexec.rules",
            "/var/crash/*/kexec-dmesg.log",
            "/var/log/kdump.log",
            "/var/crash/*/vmcore-creation.status",
        ])
        self.add_copy_spec("/var/crash/*/vmcore-dmesg.txt",
                           tags="vmcore_dmesg")
        try:
            path = self.read_kdump_conffile()
        except Exception:  # pylint: disable=broad-except
            # set no filesystem and default path
            path = "/var/crash"

        self.add_dir_listing(path, recursive=True)
        self.add_copy_spec(f"{path}/*/vmcore-dmesg.txt")
        self.add_copy_spec(f"{path}/*/kexec-dmesg.log")
        self.add_copy_spec(f"{path}/*/vmcore-creation.status")

        # collect the latest vmcore created in the last 24hrs <= 2GB
        if self.get_option("get-vm-core"):
            self.add_copy_spec(f"{path}/*/vmcore", sizelimit=2048, maxage=24)

        # collect status via kdumpctl
        self.add_cmd_output([
            "kdumpctl status",
            "kdumpctl estimate",
        ])


class DebianKDump(KDump, DebianPlugin, UbuntuPlugin):

    files = ('/etc/default/kdump-tools',)
    packages = ('kdump-tools',)

    option_list = [
        PluginOpt("get-vm-core", default=False, val_type=bool,
                  desc="collect memory dumps")
    ]

    def read_kdump_conffile(self):
        """ Parse /etc/default/kdump-tools """
        path = "/var/crash"

        kdump = '/etc/default/kdump-tools'
        with open(kdump, 'r', encoding='UTF-8') as file:
            for line in file:
                line = line.strip()
                if line.startswith("KDUMP_COREDIR"):
                    path = line.split('=')[1].strip('"')

        return path

    def setup(self):
        super().setup()

        initramfs_img = "/var/lib/kdump/initrd.img-" + platform.release()
        if self.path_exists(initramfs_img):
            self.add_cmd_output(f"lsinitramfs -l {initramfs_img}")

        self.add_cmd_output("kdump-config show")

        self.add_copy_spec([
            "/etc/default/kdump-tools"
        ])

        try:
            path = self.read_kdump_conffile()
        except Exception:  # pylint: disable=broad-except
            # set default path of coredir
            path = "/var/crash"

        self.add_dir_listing(path, recursive=True)
        self.add_copy_spec([
            f"{path}/kexec_cmd",
            f"{path}/kdump_lock",
            f"{path}/*/dmesg*",
        ])
        self.add_copy_spec(f"{path}/linux-image-*", sizelimit=2048, maxage=24)

        # collect the latest dump created in the last 24hrs <= 2GB
        if self.get_option("get-vm-core"):
            self.add_copy_spec(f"{path}/*/dump*", sizelimit=2048, maxage=24)


class CosKDump(KDump, CosPlugin):

    option_list = [
        PluginOpt(name="collect-kdumps", default=False,
                  desc="Collect existing kdump files"),
    ]

    def setup(self):
        super().setup()
        self.add_dir_listing('/var/kdump*', recursive=True)
        if self.get_option("collect-kdumps"):
            self.add_copy_spec(["/var/kdump-*"])


class AzureKDump(KDump, AzurePlugin):

    files = ('/etc/kdump.conf',)
    packages = ('kexec-tools',)

    option_list = [
        PluginOpt("get-vm-core", default=False, val_type=bool,
                  desc="collect vm core")
    ]

    def read_kdump_conffile(self):
        """ Parse /etc/kdump file """
        path = "/var/crash"

        kdump = '/etc/kdump.conf'
        with open(kdump, 'r', encoding='UTF-8') as file:
            for line in file:
                if line.startswith("path"):
                    path = line.split()[1]

        return path

    def setup(self):
        super().setup()

        self.add_copy_spec([
            "/etc/kdump.conf",
            "/usr/lib/udev/rules.d/*kexec.rules"
        ])

        try:
            path = self.read_kdump_conffile()
        except Exception:  # pylint: disable=broad-except
            # set no filesystem and default path
            path = "/var/crash"

        self.add_dir_listing(path, recursive=True)
        self.add_copy_spec(f"{path}/*/vmcore-dmesg.txt")
        self.add_copy_spec(f"{path}/*/kexec-dmesg.log")
        self.add_copy_spec(f"{path}/*/vmcore-creation.status")

        # collect the latest vmcore created in the last 24hrs <= 2GB
        if self.get_option("get-vm-core"):
            self.add_copy_spec(f"{path}/*/vmcore", sizelimit=2048, maxage=24)

# vim: set et ts=4 sw=4 :
