# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import logging
import unittest

try:
    import json
except ImportError:
    import simplejson as json

from sos.report import SoSReport
from sos.report.plugins import Plugin, PluginOpt
from sos.report.reporting import (Report, Section, Command, CopiedFile,
                                  CreatedFile, Alert, PlainTextReport)
from sos.policies.distros import LinuxPolicy
from sos.policies.init_systems import InitSystem


class ReportTest(unittest.TestCase):

    def test_empty(self):
        report = Report()

        expected = json.dumps({})

        self.assertEqual(expected, str(report))

    def test_nested_section(self):
        report = Report()
        section = Section(name="section")
        report.add(section)

        expected = json.dumps({"section": {}})

        self.assertEqual(expected, str(report))

    def test_multiple_sections(self):
        report = Report()
        section = Section(name="section")
        report.add(section)

        section2 = Section(name="section2")
        report.add(section2)

        expected = json.dumps({"section": {},
                               "section2": {}, })

        self.assertEqual(expected, str(report))

    def test_deeply_nested(self):
        report = Report()
        section = Section(name="section")
        command = Command(name="a command", return_code=0,
                          href="does/not/matter")

        section.add(command)
        report.add(section)

        expected = json.dumps({"section": {
            "commands": [{"name": "a command",
                          "return_code": 0,
                          "href": "does/not/matter"}]}})

        self.assertEqual(expected, str(report))


class TestPlainReport(unittest.TestCase):

    def setUp(self):
        self.report = Report()
        self.section = Section(name="plugin")
        self.div = '\n' + PlainTextReport.PLUGDIVIDER
        self.pluglist = "Loaded Plugins:\n{pluglist}"
        self.defaultheader = ''.join([
            self.pluglist.format(pluglist="  plugin"),
            self.div,
            "\nplugin\n"
        ])

    def test_basic(self):
        self.assertEqual(self.pluglist.format(pluglist=""),
                         PlainTextReport(self.report).unicode())

    def test_one_section(self):
        self.report.add(self.section)

        self.assertEqual(self.defaultheader,
                         PlainTextReport(self.report).unicode() + '\n')

    def test_two_sections(self):
        section1 = Section(name="first")
        section2 = Section(name="second")
        self.report.add(section1, section2)

        self.assertEqual(''.join([
            self.pluglist.format(pluglist="  first  second"),
            self.div,
            "\nfirst",
            self.div,
            "\nsecond"
        ]),
            PlainTextReport(self.report).unicode())

    def test_command(self):
        cmd = Command(name="ls -al /foo/bar/baz",
                      return_code=0,
                      href="sos_commands/plugin/ls_-al_foo.bar.baz")
        self.section.add(cmd)
        self.report.add(self.section)

        self.assertEqual(''.join([
            self.defaultheader,
            "-  commands executed:\n  * ls -al /foo/bar/baz"
        ]),
            PlainTextReport(self.report).unicode())

    def test_copied_file(self):
        cf = CopiedFile(name="/etc/hosts", href="etc/hosts")
        self.section.add(cf)
        self.report.add(self.section)

        self.assertEqual(''.join([
            self.defaultheader,
            "-  files copied:\n  * /etc/hosts"
        ]),
            PlainTextReport(self.report).unicode())

    def test_created_file(self):
        crf = CreatedFile(name="sample.txt",
                          href="../sos_strings/sample/sample.txt")
        self.section.add(crf)
        self.report.add(self.section)

        self.assertEqual(''.join([
            self.defaultheader,
            "-  files created:\n  * sample.txt"
        ]),
            PlainTextReport(self.report).unicode())

    def test_alert(self):
        alrt = Alert("this is an alert")
        self.section.add(alrt)
        self.report.add(self.section)

        self.assertEqual(''.join([
            self.defaultheader,
            "-  alerts:\n  ! this is an alert"
        ]),
            PlainTextReport(self.report).unicode())


class MockOptions:
    all_logs = False
    dry_run = False
    log_size = 25
    allow_system_changes = False
    skip_commands = []
    skip_files = []
    plugopts = []


class MockPlugin(Plugin):

    option_list = [
        PluginOpt('baz', default=False),
        PluginOpt('empty', default=None),
        PluginOpt('test_option', default='foobar', val_type=str)
    ]

    def __init__(self, commons):
        super().__init__(commons=commons)


class SetTunablesPresetSpacesTest(unittest.TestCase):

    def setUp(self):
        self.commons = {
            'sysroot': '/',
            'policy': LinuxPolicy(init=InitSystem()),
            'cmdlineopts': MockOptions(),
            'devices': {}
        }
        self.plugin = MockPlugin(self.commons)

        self.report = SoSReport.__new__(SoSReport)
        self.report.opts = MockOptions()
        self.report.soslog = logging.getLogger('sos_test_set_tunables')
        self.report.loaded_plugins = [('mock', self.plugin)]

    def set_tunables(self, plugopts):
        """Run _set_tunables with the given preset-style plugopts list."""
        self.report.opts.plugopts = plugopts
        self.report._set_tunables()

    def test_plugopt_without_spaces_still_parses(self):
        self.set_tunables(['mock.baz=True'])
        self.assertIs(self.plugin.options['baz'].value, True)

    def test_plugopt_with_spaces_around_equals(self):
        self.set_tunables(['mock.baz = True'])
        self.assertIs(self.plugin.options['baz'].value, True)

    def test_plugopt_with_spaces_disables_option(self):
        self.set_tunables(['mock.baz = False'])
        self.assertIs(self.plugin.options['baz'].value, False)

    def test_plugopt_string_value_with_spaces_around_equals(self):
        self.set_tunables(['mock.test_option = bar'])
        self.assertEqual(self.plugin.options['test_option'].value,
                         'bar')

    def test_unknown_plugopt_exits_even_with_spaces(self):
        # An unknown option name (with surrounding whitespace) should still
        # be reported as unknown rather than silently mis-stripped.
        with self.assertRaises(SystemExit):
            self.set_tunables(['mock.bogus = True'])


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
