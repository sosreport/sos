# Copyright (C) 2026 Suraj Patil <surajpatil522@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class IrqBalance(Plugin, IndependentPlugin):

    short_desc = 'IRQ balancing daemon'

    plugin_name = 'irqbalance'
    profiles = ('system', 'hardware', 'performance')

    packages = ('irqbalance',)
    services = ('irqbalance',)

    def setup(self):
        # The unit reads its arguments from two environment files: the
        # packaged defaults and an optional administrator override. Which
        # of the two paths is used depends on how the package was built,
        # so collect both conventional locations.
        self.add_copy_spec([
            '/etc/sysconfig/irqbalance',
            '/etc/default/irqbalance',
            '/usr/lib/systemd/system/irqbalance.service.d/',
            '/etc/systemd/system/irqbalance.service.d/',
        ])

        self.add_dir_listing('/run/irqbalance', tags='irqbalance_run_dir')

        self.add_cmd_output('irqbalance --version',
                            tags='irqbalance_version')

        self.add_journal(units='irqbalance')

# vim: set et ts=4 sw=4 :
