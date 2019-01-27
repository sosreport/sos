# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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

    def fstab_parse_fs(self, device):
        with open('/etc/fstab', 'r') as fp:
            for line in fp:
                if line.startswith((device)):
                    return line.split()[1].rstrip('/')
        return ""

    def read_kdump_conffile(self):
        fs = ""
        path = "/var/crash"

        with open('/etc/kdump.conf', 'r') as fp:
            for line in fp:
                if line.startswith("path"):
                    path = line.split()[1]
                elif line.startswith(("ext2", "ext3", "ext4", "xfs")):
                    device = line.split()[1]
                    fs = self.fstab_parse_fs(device)
        return fs + path

    def setup(self):
        self.add_copy_spec([
            "/etc/kdump.conf",
            "/etc/udev/rules.d/*kexec.rules",
            "/var/crash/*/vmcore-dmesg.txt"
        ])
        try:
            path = self.read_kdump_conffile()
        except Exception:
            # set no filesystem and default path
            path = "/var/crash"

        self.add_copy_spec("{}/*/vmcore-dmesg.txt".format(path))


class DebianKDump(KDump, DebianPlugin, UbuntuPlugin):

    files = ('/etc/default/kdump-tools',)
    packages = ('kdump-tools',)

    def setup(self):
        self.add_copy_spec([
            "/etc/default/kdump-tools"
        ])

# vim: set et ts=4 sw=4 :
