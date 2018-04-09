# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Last(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """login information
    """

    plugin_name = 'last'
    profiles = ('system',)

    def setup(self):
        self.add_cmd_output("last", root_symlink="last")
        self.add_cmd_output([
            "last reboot",
            "last shutdown",
            "lastlog"
        ])

# vim: et ts=4 sw=4
