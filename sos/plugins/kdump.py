# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import (Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin,
                         CosPlugin)


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
        self.add_copy_spec([
            "/etc/kdump.conf",
            "/etc/udev/rules.d/*kexec.rules",
            "/var/crash/*/vmcore-dmesg.txt"
        ])


class DebianKDump(KDump, DebianPlugin, UbuntuPlugin):

    files = ('/etc/default/kdump-tools',)
    packages = ('kdump-tools',)

    def setup(self):
        self.add_copy_spec([
            "/etc/default/kdump-tools"
        ])


class CosKDump(KDump, CosPlugin):

    option_list = [
        ("all_dumps", "enable capture for all kernel dumps", "", False),
        ("latest_dump", "enable capture for latest kernel crash dump",
            "", False),
    ]

    def setup(self):
        super(CosKDump, self).setup()
        self.add_cmd_output('ls -alRh /var/kdump*')
        if self.get_option("all_dumps"):
            self.add_copy_spec([
                "/var/kdump-*"
            ])
        if self.get_option("latest_dump"):
            self.add_copy_spec([
                "/var/kdump"
            ])

# vim: set et ts=4 sw=4 :
