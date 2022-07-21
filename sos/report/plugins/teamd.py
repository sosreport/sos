# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Teamd(Plugin, IndependentPlugin):

    short_desc = 'Network Interface Teaming'
    plugin_name = 'teamd'
    profiles = ('network', 'hardware', )

    packages = ('teamd',)

    def setup(self):
        self.add_copy_spec([
            "/etc/dbus-1/system.d/teamd.conf",
            "/usr/lib/systemd/system/teamd@.service"
        ])

        self.add_device_cmd([
            "teamdctl %(dev)s state",
            "teamdctl %(dev)s state dump",
            "teamdctl %(dev)s config dump",
            "teamnl %(dev)s option",
            "teamnl %(dev)s ports"
        ], devices='team')

# vim: set et ts=4 sw=4 :
