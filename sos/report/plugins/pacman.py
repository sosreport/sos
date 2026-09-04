# Copyright (C) 2023 Marcel Wiegand <wiegand@linux.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, ArchPlugin


class Pacman(Plugin, ArchPlugin):

    short_desc = "Package management utility for Arch Linux"

    plugin_name = "pacman"
    profiles = ("system", "sysmgmt", "packagemanager")

    def setup(self):
        self.add_copy_spec([
            "/etc/pacman.conf",
            "/etc/pacman.d",
            "/var/log/pacman.log",
        ])

        self.add_cmd_output([
            "pacman -Qi",
            "pacman -Qu",
            "pacman -Qkk",
        ])

    def postproc(self):
        # Scrub credentials in http URIs
        self.do_paths_http_sub([
            '/etc/pacman.conf',
            '/etc/pacman.d/*',
            '/var/log/pacman.log',
        ])
