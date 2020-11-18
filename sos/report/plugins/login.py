# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Login(Plugin, IndependentPlugin):

    short_desc = 'login information'

    plugin_name = 'login'
    profiles = ('system', 'identity')

    def setup(self):
        self.add_cmd_output("last", root_symlink="last")
        self.add_cmd_output([
            "last reboot",
            "last shutdown",
            "lastlog",
            "lastlog -u 0-999",
            "lastlog -u 1000-60000",
            "lastlog -u 60001-65536",
            "lastlog -u 65537-4294967295"
        ])

        self.add_copy_spec([
            "/etc/login.defs",
            "/etc/default/useradd",
        ])

# vim: et ts=4 sw=4
