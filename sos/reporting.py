"""This provides a restricted tag language to define the sosreport index/report"""

try:
    import json
except ImportError:
    import simplejson as json

# PYCOMPAT
from six import iteritems

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


class PlainTextReport(object):
    """Will generate a plain text report from a top_level Report object"""

    LEAF  = "  * %(name)s"
    ALERT = "  ! %s"
    NOTE  = "  * %s"
    DIVIDER = "=" * 72

    subsections = (
        (Command, LEAF,      "-  commands executed:"),
        (CopiedFile, LEAF,   "-  files copied:"),
        (CreatedFile, LEAF,  "-  files created:"),
        (Alert, ALERT,       "-  alerts:"),
        (Note, NOTE,         "-  notes:"),
    )

    buf = []

    def __init__(self, report_node):
        self.report_node = report_node

    def __str__(self):
        self.buf = buf = []
        for section_name, section_contents in sorted(iteritems(self.report_node.data)):
            buf.append(section_name + "\n" + self.DIVIDER)
            for type_, format_, header in self.subsections:
                self.process_subsection(section_contents, type_.ADDS_TO, header, format_)

        return "\n".join(buf)

    def process_subsection(self, section, key, header, format_):
        if key in section:
            self.buf.append(header)
            for item in section.get(key):
                self.buf.append(format_ % item)

class HtmlReport(object):
    """Will generate a html report from a top_level Report object"""

    LEAF  = "<div class=\"leaf\">%(name)s</div>"
    ALERT = "<div class=\"alert\">%s</div>"
    NOTE  = "<div class=\"note\">%s</div>"
    DIVIDER = "<hr class=\"divider\" />"

    subsections = (
        (Command, LEAF,      "-  commands executed:"),
        (CopiedFile, LEAF,   "-  files copied:"),
        (CreatedFile, LEAF,  "-  files created:"),
        (Alert, ALERT,       "-  alerts:"),
        (Note, NOTE,         "-  notes:"),
    )

    buf = []

    def __init__(self, report_node):
        self.report_node = report_node

    def __str__(self):
        self.buf = buf = []
        buf.append(self.header_text())
        for section_name, section_contents in sorted(iteritems(self.report_node.data)):
            buf.append(section_name + "\n" + self.DIVIDER)
            for type_, format_, header in self.subsections:
                self.process_subsection(section_contents, type_.ADDS_TO, header, format_)
        buf.append(self.footer_text())
        return "\n".join(buf)

    def header_text(self):
        txt = []
        txt.append("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
            <head>
              <link rel="stylesheet" type="text/css" media="screen" href="donot.css" />
              <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
              <title>Sos System Report</title>
            </head>
            <body>
        """)
        return txt

    def footer_text(self):
        txt = []
        txt.append("</body></html>")
        return txt

    def process_subsection(self, section, key, header, format_):
        if key in section:
            self.buf.append(header)
            for item in section.get(key):
                self.buf.append(format_ % item)
