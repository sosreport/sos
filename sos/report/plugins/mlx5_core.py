# Copyright (C) 2024 Nvidia Corporation,
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Mlx5_core(Plugin, IndependentPlugin):
    """The mlx5_core plugin is aimed at collecting debug information related to
    Mellenox 5th generation network adapters core driver
    """
    short_desc = 'Mellanox 5th generation network adapters (ConnectX series)\
    core driver'
    plugin_name = 'mlx5_core'
    profiles = ('hardware', )

    def setup(self):
        self.add_copy_spec([
            '/sys/kernel/debug/mlx5/0000:*/*',
        ])


# vim: set et ts=4 sw=4 :
