# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Dbus(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """D-Bus message bus"""

    plugin_name = "dbus"
    profiles = ('system',)
    packages = ('dbus',)

    def setup(self):
        self.add_copy_spec([
            "/etc/dbus-1",
            "/var/lib/dbus/machine-id"
        ])

        self.add_cmd_output([
            "busctl list --no-pager",
            "busctl status"
        ])

# vim: set et ts=4 sw=4 :
