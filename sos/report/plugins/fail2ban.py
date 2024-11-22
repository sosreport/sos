# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Fail2Ban(Plugin, IndependentPlugin):

    short_desc = "Fail2Ban daemon"

    plugin_name = "fail2ban"
    profiles = ('security',)
    packages = ('fail2ban', 'fail2ban-server')
    servicess = ('fail2ban',)

    def setup(self):

        self.add_copy_spec([
            '/etc/fail2ban',
        ])

        self.add_cmd_output([
            'fail2ban-client status',
            'fail2ban-client banned',
        ])
