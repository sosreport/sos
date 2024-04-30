# Copyright (C) 2024 Alan Baghumian <alan.baghumian@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class MicroOVN(Plugin, UbuntuPlugin):
    """The MicroOVN plugin collects the current status of the microovn
    snap.

    It will collect journald logs as well as output from various microovn
    commands.
    """

    short_desc = 'MicroOVN Snap'
    plugin_name = "microovn"
    profiles = ('network', 'virt')

    packages = ('microovn', )
    commands = ('microovn', )

    def setup(self):
        self.add_journal(units="snap.microovn.*")

        microovn_subcmds = [
            'cluster list',
            'status',
            'certificates list',
            '--version'
        ]
        self.add_cmd_output([
            f"microovn {subcmd}" for subcmd in microovn_subcmds
        ])
