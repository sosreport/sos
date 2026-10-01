# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Lldpd(Plugin, IndependentPlugin):

    short_desc = 'LLDP daemon'

    plugin_name = 'lldpd'
    profiles = ('network', 'hardware')

    packages = ('lldpd',)
    services = ('lldpd',)

    def setup(self):
        # The unit sources its arguments from whichever of the two
        # conventional environment files the distribution ships.
        self.add_copy_spec([
            '/etc/lldpd.conf',
            '/etc/lldpd.d/',
            '/etc/default/lldpd',
            '/etc/sysconfig/lldpd',
        ])

        self.add_cmd_output([
            'lldpcli show chassis',
            'lldpcli show configuration',
            'lldpcli show interfaces details',
            'lldpcli show neighbors details',
            'lldpcli show statistics',
        ], tags='lldpcli_show')

        self.add_journal(units='lldpd')

# vim: set et ts=4 sw=4 :
