# Copyright (C) 2024 Javier Blanco <javier@jblanco.es>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Qdevice(Plugin, IndependentPlugin):
    short_desc = 'qdevice information'

    plugin_name = 'qdevice'
    packages = ('corosync-qnetd',)

    def setup(self):
        self.add_cmd_output([
            "pcs qdevice status net --full"
        ])


# vim: et ts=4 sw=4
