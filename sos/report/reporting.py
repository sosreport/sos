# Copyright (C) 2014 Red Hat, Inc.,
#   Bryn M. Reeves <bmr@redhat.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

""" This provides a restricted tag language to define the sosreport
    index/report
"""

try:
    import json
except ImportError:
    import simplejson as json


class Node(object):

    def __str__(self):
        return json.dumps(self.data)

    def can_add(self, node):
        return False


class Leaf(Node):
    """Marker class that can be added to a Section node"""
    pass


class Report(Node):
    """The root element of a report. This is a container for sections."""

    def __init__(self):
        self.data = {}

    def can_add(self, node):
        return isinstance(node, Section)

    def add(self, *nodes):
        for node in nodes:
            if self.can_add(node):
                self.data[node.name] = node.data


def _decode(s):
    """returns a string text for a given unicode/str input"""
    return (s if isinstance(s, str) else s.decode('utf8', 'ignore'))


class Section(Node):
    """A section is a container for leaf elements. Sections may be nested
    inside of Report objects only."""

    def __init__(self, name):
        self.name = _decode(name)
        self.data = {}

    def can_add(self, node):
        return isinstance(node, Leaf)

    def add(self, *nodes):
        for node in nodes:
            if self.can_add(node):
                self.data.setdefault(node.ADDS_TO, []).append(node.data)


class Command(Leaf):

    ADDS_TO = "commands"

    def __init__(self, name, return_code, href):
        self.data = {"name": _decode(name),
                     "return_code": return_code,
                     "href": _decode(href)}


class CopiedFile(Leaf):

    ADDS_TO = "copied_files"

    def __init__(self, name, href):
        self.data = {"name": _decode(name),
                     "href": _decode(href)}


class CreatedFile(Leaf):

    ADDS_TO = "created_files"

    def __init__(self, name, href):
        self.data = {"name": _decode(name),
                     "href": _decode(href)}


class Alert(Leaf):

    ADDS_TO = "alerts"

    def __init__(self, content):
        self.data = _decode(content)


class Note(Leaf):

    ADDS_TO = "notes"

    def __init__(self, content):
        self.data = _decode(content)


def ends_bs(string):
    """ Return True if 'string' ends with a backslash, and False otherwise.

        Define this as a named function for no other reason than that pep8
        now forbids binding of a lambda expression to a name:

        'E731 do not assign a lambda expression, use a def'
    """
    return string.endswith('\\')


class PlainTextReport(object):
    """Will generate a plain text report from a top_level Report object"""

    HEADER = ""
    FOOTER = ""
    LEAF = "  * %(name)s"
    ALERT = "  ! %s"
    NOTE = "  * %s"
    PLUGLISTHEADER = "Loaded Plugins:"
    PLUGLISTITEM = "  {name}"
    PLUGLISTSEP = "\n"
    PLUGLISTMAXITEMS = 5
    PLUGLISTFOOTER = ""
    PLUGINFORMAT = "{name}"
    PLUGDIVIDER = "=" * 72

    subsections = (
        (Command, LEAF,      "-  commands executed:", ""),
        (CopiedFile, LEAF,   "-  files copied:",      ""),
        (CreatedFile, LEAF,  "-  files created:",     ""),
        (Alert, ALERT,       "-  alerts:",            ""),
        (Note, NOTE,         "-  notes:",             ""),
    )

    line_buf = []

    def __init__(self, report_node):
        self.report_data = sorted(dict.items(report_node.data))

    def unicode(self):
        self.line_buf = line_buf = []

        if (len(self.HEADER) > 0):
            line_buf.append(self.HEADER)

        # generate section/plugin list, split long list to multiple lines
        line_buf.append(self.PLUGLISTHEADER)
        line = ""
        i = 0
        plugcount = len(self.report_data)
        for section_name, _ in self.report_data:
            line += self.PLUGLISTITEM.format(name=section_name)
            i += 1
            if (i % self.PLUGLISTMAXITEMS == 0) and (i < plugcount):
                line += self.PLUGLISTSEP
        line += self.PLUGLISTFOOTER
        line_buf.append(line)

        for section_name, section_contents in self.report_data:
            line_buf.append(self.PLUGDIVIDER)
            line_buf.append(self.PLUGINFORMAT.format(name=section_name))
            for type_, format_, header, footer in self.subsections:
                self.process_subsection(section_contents, type_.ADDS_TO,
                                        header, format_, footer)

        if (len(self.FOOTER) > 0):
            line_buf.append(self.FOOTER)

        output = u'\n'.join(map(lambda i: (i if isinstance(i, str)
                                           else i.decode('utf8', 'ignore')),
                                line_buf))
        return output

    def process_subsection(self, section, key, header, format_, footer):
        if key in section:
            self.line_buf.append(header)
            for item in sorted(
                    section.get(key),
                    key=lambda x: x["name"] if isinstance(x, dict) else ''
            ):
                self.line_buf.append(format_ % item)
            if (len(footer) > 0):
                self.line_buf.append(footer)


class HTMLReport(PlainTextReport):
    """Will generate a HTML report from a top_level Report object"""

    HEADER = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
        <head>
            <meta http-equiv="Content-Type" content="text/html;
                  charset=utf-8" />
            <title>Sos System Report</title>
            <style type="text/css">
                td {
                    padding: 0 5px;
                   }
            </style>
        </head>
        <body>\n"""
    FOOTER = "</body></html>"
    LEAF = '<li><a href="%(href)s">%(name)s</a></li>'
    ALERT = "<li>%s</li>"
    NOTE = "<li>%s</li>"
    PLUGLISTHEADER = "<h3>Loaded Plugins:</h3><table><tr>"
    PLUGLISTITEM = '<td><a href="#{name}">{name}</a></td>\n'
    PLUGLISTSEP = "</tr>\n<tr>"
    PLUGLISTMAXITEMS = 5
    PLUGLISTFOOTER = "</tr></table>"
    PLUGINFORMAT = '<h2 id="{name}">Plugin <em>{name}</em></h2>'
    PLUGDIVIDER = "<hr/>\n"

    subsections = (
        (Command, LEAF,      "<p>Commands executed:</p><ul>", "</ul>"),
        (CopiedFile, LEAF,   "<p>Files copied:</p><ul>",      "</ul>"),
        (CreatedFile, LEAF,  "<p>Files created:</p><ul>",     "</ul>"),
        (Alert, ALERT,       "<p>Alerts:</p><ul>",            "</ul>"),
        (Note, NOTE,         "<p>Notes:</p><ul>",             "</ul>"),
    )


class JSONReport(PlainTextReport):
    """Will generate a JSON report from a top_level Report object"""

    def unicode(self):
        output = json.dumps(self.report_data, indent=4, ensure_ascii=False)
        return output

# vim: set et ts=4 sw=4 :
