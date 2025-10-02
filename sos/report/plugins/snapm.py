# Copyright (C) 2025 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Snapm(Plugin, RedHatPlugin):

    short_desc = 'Snapsot manager'

    plugin_name = 'snapm'
    profiles = ('boot', 'system', 'storage')

    packages = (
        'python3-snapm',
        'snapm',
    )

    def setup(self):
        self.add_copy_spec([
            "/etc/snapm",
        ])

        self.add_cmd_output([
            "snapm snapset list",
            "snapm snapshot list",
            "snapm plugin list",
            "snapm schedule list",
            "snapm -vv --debug=all snapset show",
        ])

# vim: set et ts=4 sw=4 :
