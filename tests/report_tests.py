#!/usr/bin/env python

import unittest
import os

try:
    import json
except ImportError:
    import simplejson as json

from sos.reporting import Report, Section, Command, CopiedFile, CreatedFile, Alert
from sos.reporting import PlainTextReport

class ReportTest(unittest.TestCase):

    def test_empty(self):
        report = Report()

        expected = json.dumps({})

        self.assertEquals(expected, str(report))

    def test_nested_section(self):
        report = Report()
        section = Section(name="section")
        report.add(section)

        expected = json.dumps({"section": {}})

        self.assertEquals(expected, str(report))

    def test_multiple_sections(self):
        report = Report()
        section = Section(name="section")
        report.add(section)

        section2 = Section(name="section2")
        report.add(section2)

        expected = json.dumps({"section": {},
                               "section2": {},})

        self.assertEquals(expected, str(report))


    def test_deeply_nested(self):
        report = Report()
        section = Section(name="section")
        command = Command(name="a command", return_code=0, href="does/not/matter")

        section.add(command)
        report.add(section)

        expected = json.dumps({"section": {"commands": [{"name": "a command",
                                                         "return_code": 0,
                                                         "href": "does/not/matter"}]}})

        self.assertEquals(expected, str(report))


class TestPlainReport(unittest.TestCase):

    def setUp(self):
        self.report = Report()
        self.section = Section(name="plugin")
        self.div = PlainTextReport.DIVIDER

    def test_basic(self):
        self.assertEquals("", str(PlainTextReport(self.report)))

    def test_one_section(self):
        self.report.add(self.section)

        self.assertEquals("plugin\n" + self.div, str(PlainTextReport(self.report)))

    def test_two_sections(self):
        section1 = Section(name="first")
        section2 = Section(name="second")
        self.report.add(section1, section2)

        self.assertEquals("first\n" + self.div + "\nsecond\n" + self.div, str(PlainTextReport(self.report)))

    def test_command(self):
        cmd = Command(name="ls -al /foo/bar/baz",
                      return_code=0,
                      href="sos_commands/plugin/ls_-al_foo.bar.baz")
        self.section.add(cmd)
        self.report.add(self.section)

        self.assertEquals("plugin\n" + self.div + "\n-  commands executed:\n  * ls -al /foo/bar/baz",
                str(PlainTextReport(self.report)))

    def test_copied_file(self):
        cf = CopiedFile(name="/etc/hosts", href="etc/hosts")
        self.section.add(cf)
        self.report.add(self.section)

        self.assertEquals("plugin\n" + self.div + "\n-  files copied:\n  * /etc/hosts",
                str(PlainTextReport(self.report)))

    def test_created_file(self):
        crf = CreatedFile(name="sample.txt")
        self.section.add(crf)
        self.report.add(self.section)

        self.assertEquals("plugin\n" + self.div + "\n-  files created:\n  * sample.txt",
                str(PlainTextReport(self.report)))

    def test_alert(self):
        alrt = Alert("this is an alert")
        self.section.add(alrt)
        self.report.add(self.section)

        self.assertEquals("plugin\n" + self.div + "\n-  alerts:\n  ! this is an alert",
                str(PlainTextReport(self.report)))

if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
