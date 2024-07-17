# Copyright (C) 2024 Alan Baghumian <alan.baghumian@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 or later of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class MicroCloud(Plugin, UbuntuPlugin):
    """The MicroCloud plugin collects the current status of the microcloud
    snap.

    It will collect journald logs as well as output from various microcloud
    commands.
    """

    short_desc = 'MicroCloud Snap'
    plugin_name = "microcloud"
    profiles = ('container',)

    packages = ('microcloud',)

    def setup(self):
        self.add_journal(units="snap.microcloud.*")

        microcloud_subcmds = [
            'cluster list',
            '--version'
        ]
        self.add_copy_spec([
            '/var/snap/microcloud/common/state/database/cluster.yaml',
            '/var/snap/microcloud/common/state/database/info.yaml',
        ])

        self.add_cmd_output([
            f"microcloud {subcmd}" for subcmd in microcloud_subcmds
        ])

# vim: set et ts=4 sw=4
