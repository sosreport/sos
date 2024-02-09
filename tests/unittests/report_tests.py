# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import unittest

try:
    import json
except ImportError:
    import simplejson as json

from sos.report.reporting import (Report, Section, Command, CopiedFile,
                                  CreatedFile, Alert, PlainTextReport)


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
        self.defaultheader = u''.join([
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

        self.assertEqual(u''.join([
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

        self.assertEqual(u''.join([
            self.defaultheader,
            "-  commands executed:\n  * ls -al /foo/bar/baz"
        ]),
            PlainTextReport(self.report).unicode())

    def test_copied_file(self):
        cf = CopiedFile(name="/etc/hosts", href="etc/hosts")
        self.section.add(cf)
        self.report.add(self.section)

        self.assertEqual(u''.join([
            self.defaultheader,
            "-  files copied:\n  * /etc/hosts"
        ]),
            PlainTextReport(self.report).unicode())

    def test_created_file(self):
        crf = CreatedFile(name="sample.txt",
                          href="../sos_strings/sample/sample.txt")
        self.section.add(crf)
        self.report.add(self.section)

        self.assertEqual(u''.join([
            self.defaultheader,
            "-  files created:\n  * sample.txt"
        ]),
            PlainTextReport(self.report).unicode())

    def test_alert(self):
        alrt = Alert("this is an alert")
        self.section.add(alrt)
        self.report.add(self.section)

        self.assertEqual(u''.join([
            self.defaultheader,
            "-  alerts:\n  ! this is an alert"
        ]),
            PlainTextReport(self.report).unicode())


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
