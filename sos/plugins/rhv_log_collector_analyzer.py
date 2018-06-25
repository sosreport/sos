# Copyright (C) 2018 Red Hat, Inc.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import os
import tempfile

from sos.plugins import Plugin, RedHatPlugin


class RhvLogCollectorAnalyzer(Plugin, RedHatPlugin):
    """RHV Log Collector Analyzer"""

    packages = (
        'rhv-log-collector-analyzer',
    )

    plugin_name = 'rhv_log_collector_analyzer'
    profiles = ('virt',)

    report = "{tempdir}/rhv-log-collector-analyer-report.html".format(
        tempdir=tempfile.gettempdir())

    def setup(self):

        self.get_command_output(
            "rhv-log-collector-analyzer"
            " --live"
            " --html={report}".format(report=self.report)
        )

        if os.path.exists(self.report):
            self.add_copy_spec("{report}".format(report=self.report))

        self.add_cmd_output(
            "rhv-log-collector-analyzer"
            " --json"
        )

    def postproc(self):
        if os.path.exists(self.report):
            os.unlink("{report}".format(report=self.report))

# vim: expandtab tabstop=4 shiftwidth=4
