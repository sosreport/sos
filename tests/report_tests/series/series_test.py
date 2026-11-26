# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, and redistribute it subject to the terms and conditions
# of version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class SeriesTest(Plugin, IndependentPlugin):

    plugin_name = 'series_test'
    short_desc = 'Tests series functionality in test suite'

    def setup(self):
        self.add_cmd_output('date', series={'count': 3, 'interval': 2})
        # uptime contains only one value on purpose, we want to
        # make sure that we test collection exactly once, and also that
        # we get a warning logged
        self.add_cmd_output('uptime', series={'count': 0})
