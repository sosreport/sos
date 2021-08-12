# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt
from glob import glob


class Boot(Plugin, IndependentPlugin):

    short_desc = 'Bootloader information'

    plugin_name = 'boot'
    profiles = ('system', 'boot')
    packages = ('grub', 'grub2', 'grub-common', 'grub2-common', 'zipl')

    option_list = [
        PluginOpt("all-images", default=False,
                  desc="collect lsinitrd for all images")
    ]

    def setup(self):
        self.add_copy_spec([
            # legacy / special purpose bootloader configs
            "/etc/milo.conf",
            "/etc/silo.conf",
            "/boot/efi/efi/redhat/elilo.conf",
            "/etc/yaboot.conf",
            "/boot/yaboot.conf"
        ])

        self.add_cmd_output("ls -lanR /boot", tags="insights_ls_boot")

        self.add_cmd_output([
            "lsinitrd",
            "ls -lanR /sys/firmware",
        ])

        self.add_cmd_output([
            "efibootmgr -v",
            "mokutil --sb-state"
        ])

        if self.get_option("all-images"):
            for image in glob('/boot/initr*.img'):
                if image[-9:] == "kdump.img":
                    continue
                self.add_cmd_output("lsinitrd %s" % image, priority=100)


# vim: set et ts=4 sw=4 :
