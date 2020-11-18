# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Dbus(Plugin, IndependentPlugin):

    short_desc = 'D-Bus message bus'

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

        self.add_env_var('DBUS_SESSION_BUS_ADDRESS')

# vim: set et ts=4 sw=4 :
