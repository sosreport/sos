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

# PYCOMPAT
import six


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


class Section(Node):
    """A section is a container for leaf elements. Sections may be nested
    inside of Report objects only."""

    def __init__(self, name):
        self.name = name
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
        self.data = {"name": name,
                     "return_code": return_code,
                     "href": href}


class CopiedFile(Leaf):

    ADDS_TO = "copied_files"

    def __init__(self, name, href):
        self.data = {"name": name,
                     "href": href}


class CreatedFile(Leaf):

    ADDS_TO = "created_files"

    def __init__(self, name):
        self.data = {"name": name}


class Alert(Leaf):

    ADDS_TO = "alerts"

    def __init__(self, content):
        self.data = content


class Note(Leaf):

    ADDS_TO = "notes"

    def __init__(self, content):
        self.data = content


def ends_bs(string):
    """ Return True if 'string' ends with a backslash, and False otherwise.

        Define this as a named function for no other reason than that pep8
        now forbids binding of a lambda expression to a name:

        'E731 do not assign a lambda expression, use a def'
    """
    return string.endswith('\\')


class PlainTextReport(object):
    """Will generate a plain text report from a top_level Report object"""

    LEAF = "  * %(name)s"
    ALERT = "  ! %s"
    NOTE = "  * %s"
    DIVIDER = "=" * 72

    subsections = (
        (Command, LEAF,      "-  commands executed:"),
        (CopiedFile, LEAF,   "-  files copied:"),
        (CreatedFile, LEAF,  "-  files created:"),
        (Alert, ALERT,       "-  alerts:"),
        (Note, NOTE,         "-  notes:"),
    )

    line_buf = []

    def __init__(self, report_node):
        self.report_node = report_node

    def unicode(self):
        self.line_buf = line_buf = []
        for section_name, section_contents in sorted(six.iteritems(
                self.report_node.data)):
            line_buf.append(section_name + "\n" + self.DIVIDER)
            for type_, format_, header in self.subsections:
                self.process_subsection(section_contents, type_.ADDS_TO,
                                        header, format_)

        # Workaround python.six mishandling of strings ending in '/' by
        # adding a single space following any '\' at end-of-line.
        # See Six issue #60.
        line_buf = [line + " " if ends_bs(line) else line for line in line_buf]

        output = u'\n'.join(map(lambda i: (i if isinstance(i, six.text_type)
                                           else six.u(i)), line_buf))
        if six.PY3:
            return output
        else:
            return output.encode('utf8')

    def process_subsection(self, section, key, header, format_):
        if key in section:
            self.line_buf.append(header)
            for item in section.get(key):
                self.line_buf.append(format_ % item)

# vim: set et ts=4 sw=4 :
