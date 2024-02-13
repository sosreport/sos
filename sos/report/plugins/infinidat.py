# Copyright (C) 2024 Alejandro Santoyo <alejandro.santoyo@canonical.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class InfinidatStorage(Plugin, IndependentPlugin):

    short_desc = 'Infinidat Storage plugin'
    plugin_name = 'infinidat'
    profiles = ('storage',)
    packages = ('host-power-tools',)

    def setup(self):
        # Get infinidat logs
        if not self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/infinihost.latest*.log",
                "/var/log/infinihost.usage*.log",
            ])
        else:
            self.add_copy_spec([
                "/var/log/infinihost*.log",
                "/var/log/buildout.*.log",
            ])

        # Get info from the infinidat boxes, etc.
        self.add_cmd_output([
            "infinihost volume list",
            "infinihost connectivity list",
            "infinihost system list",
            "infinihost pool list",
            "infinihost snapshot list",
            "infinihost --version"
        ])

# vim: set et ts=4 sw=4 :
