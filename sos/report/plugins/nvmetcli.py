# Copyright (C) 2020 Red Hat, Inc., Nitin Yewale <nyewale@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class NvmetCli(Plugin, IndependentPlugin):

    short_desc = 'Collect config and system information for nvmetcli'

    packages = ('nvmetcli', )
    profiles = ('storage', )
    plugin_name = 'nvmetcli'

    def setup(self):
        self.add_cmd_output([
            "nvmetcli ls"
        ])
        self.add_journal(units=["nvme", "nvmet", "nvmet_rdma"])
        self.add_copy_spec([
            "/sys/kernel/config/nvmet",
            "/etc/nvmet/config.json",
        ])

# vim: set et ts=4 sw=4 :
