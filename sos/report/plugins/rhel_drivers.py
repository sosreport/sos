# Copyright (C) 2025 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class RhelDrivers(Plugin, RedHatPlugin):

    short_desc = 'RHEL-drivers information'

    plugin_name = 'rhel_drivers'
    profiles = ('system', 'kernel', 'ai',)
    packages = ('rhel-drivers',)

    def setup(self):
        self.add_cmd_output([
            "rhel-drivers list --installed",
            "rhel-drivers --verbose list --installed",
            "rhel-drivers list --available",
            "rhel-drivers --verbose list --available",
        ])

# vim: et ts=4 sw=4
