# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re

from sos_tests import StageOneOutputTest


class ReportHelpTest(StageOneOutputTest):
    """Ensure that --help gives the expected output in the expected format

    :avocado: tags=stageone
    """

    sos_cmd = 'report --help'

    def test_all_help_sections_present(self):
        self.assertOutputContains('Global Options:')
        self.assertOutputContains('Report Options:')
        self.assertOutputContains('Cleaner/Masking Options:')


class ReportListPluginsTest(StageOneOutputTest):
    """Ensure that --list-plugins gives the expected output

    :avocado: tags=stageone
    """

    sos_cmd = 'report --list-plugins'

    def test_all_plugin_sections_present(self):
        self.assertOutputContains('plugins are currently enabled:')
        self.assertOutputContains('plugins are currently disabled:')
        self.assertOutputContains('options are available for ALL plugins:')
        self.assertOutputContains('plugin options are available:')
        self.assertOutputContains('Profiles:')

    def test_no_missing_plugin_descriptions(self):
        _out = re.search("The following plugins are currently enabled:(.*?)"
                         "The following plugins are currently disabled:",
                         self.cmd_output.stdout, re.S).group(1).splitlines()
        for ln in _out:
            # Ignore newlines
            if not ln:
                continue
            assert len(ln) > 1, "Plugin '%s' missing description" % ln[0]
