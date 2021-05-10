# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, SoSPredicate


class Grub2(Plugin, IndependentPlugin):

    short_desc = 'GRUB2 bootloader'

    plugin_name = 'grub2'
    profiles = ('boot',)
    packages = ('grub2', 'grub2-efi', 'grub2-common')

    def setup(self):

        self.add_file_tags({
            '/boot/grub2/grub.cfg': 'grub2_cfg',
            '/boot/efi/.*/grub.cfg': 'grub2_efi_cfg'
        })

        self.add_copy_spec([
            "/boot/efi/EFI/*/grub.cfg",
            "/boot/grub2/grub.cfg",
            "/boot/grub2/grubenv",
            "/boot/grub/grub.cfg",
            "/boot/loader/entries",
            "/etc/default/grub",
            "/etc/grub2.cfg",
            "/etc/grub.d"
        ])

        self.add_cmd_output("ls -lanR /boot", tags="ls_boot")
        # call grub2-mkconfig with GRUB_DISABLE_OS_PROBER=true to prevent
        # possible unwanted loading of some kernel modules
        # further, check if the command supports --no-grubenv-update option
        # to prevent removing of extra args in $kernel_opts, and (only) if so,
        # call the command with this argument
        grub_cmd = 'grub2-mkconfig'
        co = {'cmd': '%s --help' % grub_cmd, 'output': '--no-grubenv-update'}
        if self.test_predicate(self, pred=SoSPredicate(self, cmd_outputs=co)):
            grub_cmd += ' --no-grubenv-update'
        self.add_cmd_output(grub_cmd, env={'GRUB_DISABLE_OS_PROBER': 'true'},
                            pred=SoSPredicate(self, kmods=['dm_mod']))

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

# vim: set et ts=4 sw=4 :
