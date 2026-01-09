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
            ln = ln.split()
            # Ignore newlines
            if not ln:
                continue
            assert len(ln) > 1, f"Plugin '{ln[0]}' missing description"

    def test_plugin_formatting(self):
        _out = re.search("The following plugins are currently enabled:(.*?)"
                         "The following plugins are currently disabled:(.*?)"
                         "The following options are available "
                         "for ALL plugins:(.*?)"
                         "The following plugin options are available:(.*?)"
                         "Profiles:",
                         self.cmd_output.stdout, re.S)
        enabled_plugins = _out.group(1).splitlines()
        disabled_plugins = _out.group(2).splitlines()
        options = _out.group(3).splitlines()
        plugin_options = _out.group(4).splitlines()
        for plug in enabled_plugins:
            # Ignore empty lines
            if not plug.strip():
                continue
            self.assertRegex(plug, r' ([\S ]){30} ([\S ])*')
        for plug in disabled_plugins:
            if not plug.strip():
                continue
            self.assertRegex(plug, r' ([\S ]){30} (inactive[ ]{6}) ([\S ])*')
        for opt in options:
            if not opt.strip():
                continue
            self.assertRegex(opt, r' ([\S ]){25} ([\d ]{15}) ([\S ])*')
        for opt in plugin_options:
            if not opt.strip():
                continue
            self.assertRegex(opt, r' ([\S ]){40} ([\S ]{15}) ([\S ])*')


class ReportListPresetsTest(StageOneOutputTest):
    """Ensure that --list-presets gives the expected output

    :avocado: tags=stageone
    """

    sos_cmd = 'report --list-presets'

    def test_presets_formatting(self):
        _out = re.search("The following presets are available:\n\n(.*)",
                         self.cmd_output.stdout, re.S)
        presets = _out.group(1).split("\n\n")
        for preset in presets:
            if not preset.strip():
                continue
            self.assertRegex(
                preset,
                r'[ ]{9}name: .*?\n[ ]{2}description: .*?(\n[ ]{9}note: .*)?'
            )
