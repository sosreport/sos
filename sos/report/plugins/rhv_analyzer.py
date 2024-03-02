# Copyright (C) 2018 Red Hat, Inc.
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class RhvAnalyzer(Plugin, RedHatPlugin):

    short_desc = 'RHV Log Collector Analyzer'

    packages = ('rhv-log-collector-analyzer',)

    plugin_name = 'rhv_analyzer'
    profiles = ('virt',)

    def setup(self):
        tool_name = 'rhv-log-collector-analyzer'
        report = f"{self.get_cmd_output_path()}/analyzer-report.html"

        self.add_cmd_output([
            f"{tool_name} --live --html={report}",
            f"{tool_name} --json"
        ])

# vim: expandtab tabstop=4 shiftwidth=4
