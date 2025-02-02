# Copyright (C) 2025 Nvidia Corporation,
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Doca(Plugin, IndependentPlugin):
    """The DOCA plugin is aimed at collecting debug information related to
    DOCA package and libraries
    """
    short_desc = 'NVIDIA DOCA package and libraries'
    plugin_name = 'doca'
    profiles = ('hardware', )
    packages = ('doca-caps',)

    def setup(self):
        doca_caps = '/opt/mellanox/doca/tools/doca_caps'
        self.add_cmd_output([
            f'{doca_caps} -v',
            f'{doca_caps} --list-devs',
            f'{doca_caps} --list-rep-devs',
            f'{doca_caps} --list-libs',
            f'{doca_caps}',
        ])

# vim: set et ts=4 sw=4 :
