# Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class HBN(Plugin, IndependentPlugin):

    short_desc = 'HBN (Host Based Networking)'
    plugin_name = "hbn"
    packages = ('hbn-repo',)

    def setup(self):
        self.add_copy_spec([
            '/etc/mellanox',
            '/var/log/doca/hbn',
            '/var/lib/hbn/etc/cumulus',
            '/var/log/sfc-install.log',
            '/usr/lib/udev',            # HBN udev rules
            '/tmp/sf_devices',          # udev renamed sf devices
            '/tmp/sfr_devices',         # udev renamed sf representor devices
            '/tmp/sfc-activated',
            '/tmp/.BR_*',               # interim files for updating hbn.conf
            '/tmp/.ENABLE_*',
            '/tmp/.LINK_*',
        ])

        self.add_journal(units="sfc")
        self.add_journal(units="sfc-state-propagation")

        self.add_cmd_output([
            "mlnx-sf -a show",                  # short cli output
            "mlnx-sf -a show --json --pretty",  # verbose json output
        ])
