# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Grub(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """GRUB bootloader
    """

    plugin_name = 'grub'
    profiles = ('boot',)
    packages = ('grub',)

    def setup(self):
        self.add_copy_spec([
            "/boot/efi/EFI/*/grub.conf",
            "/boot/grub/grub.conf",
            "/boot/grub/device.map",
            "/etc/grub.conf",
            "/etc/grub.d"
        ])

    def postproc(self):
        self.do_path_regex_sub(
            r".*\/grub.conf",
            r"(password\s*)(--md5\s*|\s*)(.*)",
            r"\1\2********"
        )

# vim: set et ts=4 sw=4 :
