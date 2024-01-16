# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class TimeoutTest(Plugin, IndependentPlugin):

    plugin_name = 'timeout_test'
    short_desc = 'Tests timeout functionality in test suite'
    plugin_timeout = 100

    def setup(self):
        self.add_cmd_output('sleep 15')
        self.add_cmd_output('echo I slept great', suggest_filename='echo_good')
        self.add_cmd_output('sleep 30', timeout=10)
