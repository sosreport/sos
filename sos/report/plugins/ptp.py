# Copyright (C) 2015 Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Ptp(Plugin, IndependentPlugin):

    short_desc = 'Precision time protocol'

    plugin_name = "ptp"
    profiles = ('system', 'services')

    packages = ('linuxptp',)

    def setup(self):
        self.add_copy_spec([
            "/etc/ptp4l.conf",
            "/etc/timemaster.conf",
            "/sys/class/ptp"
        ])

# vim: et ts=4 sw=4
