# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Grub2(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Bootloader information
    """

    plugin_name = 'grub2'
    packages = ('grub2',)

    def setup(self):
        self.add_copy_specs([
            "/boot/efi/EFI/*/grub.cfg",
            "/boot/grub2/grub.cfg",
            "/boot/grub2/grubenv",
            "/boot/grub/grub.cfg",
            "/etc/default/grub",
            "/etc/grub2.cfg",
            "/etc/grub.d"
        ])
        self.add_cmd_outputs([
            "ls -lanR /boot",
            "grub2-mkconfig"
        ])

    def postproc(self):
        # the trailing space is required; python treats '_' as whitespace
        # causing the passwd_exp to match pbkdf2 passwords and mangle them.
        passwd_exp = r"(password )\s*(\S*)\s*(\S*)"
        passwd_pbkdf2_exp = r"(password_pbkdf2)\s*(\S*)\s*(\S*)"
        passwd_sub = r"\1 \2 ********"
        passwd_pbkdf2_sub = r"\1 \2 grub.pbkdf2.********"

        self.do_cmd_output_sub(
            "grub2-mkconfig",
            passwd_pbkdf2_exp,
            passwd_pbkdf2_sub
        )
        self.do_cmd_output_sub(
            "grub2-mkconfig",
            passwd_exp,
            passwd_sub
        )

        self.do_path_regex_sub(
            r".*\/grub\.",
            passwd_exp,
            passwd_sub
        )

        self.do_path_regex_sub(
            r".*\/grub\.",
            passwd_pbkdf2_exp,
            passwd_pbkdf2_sub
        )

# vim: et ts=4 sw=4
