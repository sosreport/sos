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


class Rhv_Analyzer(Plugin, RedHatPlugin):

    short_desc = 'RHV Log Collector Analyzer'

    packages = ('rhv-log-collector-analyzer',)

    plugin_name = 'rhv_analyzer'
    profiles = ('virt',)

    def setup(self):
        tool_name = 'rhv-log-collector-analyzer'
        report = "{dircmd}/analyzer-report.html".format(
            dircmd=self.get_cmd_output_path()
        )

        self.add_cmd_output(
            "{tool_name}"
            " --live"
            " --html={report}".format(
                report=report, tool_name=tool_name)
        )

        self.add_cmd_output(
            "{tool_name}"
            " --json".format(tool_name=tool_name)
        )

# vim: expandtab tabstop=4 shiftwidth=4
