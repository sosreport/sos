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

    short_desc = 'HBN (Host Based Network)'
    plugin_name = "hbn"
    packages = ('hbn-repo',)

    def setup(self):
        self.add_copy_spec([
            '/etc/mellanox',
            '/var/log/doca/hbn',
            '/var/lib/hbn/etc/cumulus',
        ])
