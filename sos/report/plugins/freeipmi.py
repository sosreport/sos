# Copyright (C) 2020 Canonical Ltd. Arif Ali <arif.ali@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class Freeipmi(Plugin, UbuntuPlugin):

    short_desc = 'Freeipmi hardware information'
    plugin_name = 'freeipmi'
    profiles = ('hardware', 'system', )

    packages = ('freeipmi-tools',)

    def setup(self):

        self.add_cmd_output([
            "bmc-info",
            "ipmi-sel",
            "ipmi-sensors",
            "ipmi-chassis --get-status",
            "ipmi-fru",
        ])

# vim: set et ts=4 sw=4 :
