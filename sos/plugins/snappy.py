# Copyright (c) 2017 Bryan Quigley <bryan.quigley@canonical.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, UbuntuPlugin, DebianPlugin, RedHatPlugin


class Snappy(Plugin, UbuntuPlugin, DebianPlugin, RedHatPlugin):
    """Snap packages
    """

    plugin_name = 'snappy'
    profiles = ('system', 'sysmgmt', 'packagemanager')
    files = ('/usr/bin/snap')

    def setup(self):
        self.add_cmd_output([
            "systemctl status snapd.service",
            "snap list --all",
            "snap --version",
            "snap changes"
        ])
        self.add_journal(units="snapd")

# vim: set et ts=4 sw=4 :
