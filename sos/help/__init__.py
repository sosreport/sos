# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import inspect
import importlib
import sys
import os

from collections import OrderedDict
from sos.component import SoSComponent
from sos.policies import import_policy
from sos.report.plugins import Plugin
from sos.utilities import bold, ImporterHelper
from textwrap import fill

try:
    TERMSIZE = min(os.get_terminal_size().columns, 120)
except Exception:
    TERMSIZE = 120


class SoSHelper(SoSComponent):
    """Provide better, more in-depth help for specific parts of sos than is
    provided in either standard --help output or in manpages.
    """

    desc = 'Detailed help infomation'
    configure_logging = False
    load_policy = False
    load_probe = False

    arg_defaults = {
        'topic': ''
    }

    def __init__(self, parser, args, cmdline):
        super(SoSHelper, self).__init__(parser, args, cmdline)
        self.topic = self.opts.topic

    @classmethod
    def add_parser_options(cls, parser):
        parser.usage = 'sos help TOPIC [options]'
        help_grp = parser.add_argument_group(
            'Help Information Options',
            'These options control what detailed information is displayed'
        )
        help_grp.add_argument('topic', metavar='TOPIC', default='', nargs='?',
                              help=('name of the topic or component to show '
                                    'help for'))

    def sanitize_topic_component(self):
        _com = self.opts.topic.split('.')[0]
        _replace = {
            'clean': 'cleaner',
            'mask': 'cleaner',
            'collect': 'collector'
        }
        if _com in _replace:
            self.opts.topic = self.opts.topic.replace(_com, _replace[_com])

    def execute(self):
        if not self.opts.topic:
            self.display_self_help()
            sys.exit(0)

        # standardize the command to the module naming pattern
        self.sanitize_topic_component()

        try:
            klass = self.get_obj_for_topic()
        except Exception as err:
            print("Could not load help for '%s': %s" % (self.opts.topic, err))
            sys.exit(1)

        if klass:
            try:
                ht = HelpSection()
                klass.display_help(ht)
                ht.display()
            except Exception as err:
                print("Error loading help: %s" % err)
        else:
            print("No help section found for '%s'" % self.opts.topic)

    def get_obj_for_topic(self):
        """Based on the help topic we're after, try to smartly decide which
        object we need to manipulate in order to get help information.
        """
        static_map = {
            'report': 'SoSReport',
            'report.plugins': 'Plugin',
            'cleaner': 'SoSCleaner',
            'collector': 'SoSCollector',
            'collector.transports': 'RemoteTransport',
            'collector.clusters': 'Cluster',
            'policies': 'Policy'
        }

        cls = None

        if self.opts.topic in static_map:
            mod = importlib.import_module('sos.' + self.opts.topic)
            cls = getattr(mod, static_map[self.opts.topic])
        else:
            _help = {
                'report.plugins.': self._get_plugin_variant,
                'policies.': self._get_policy_by_name,
                'collector.transports.': self._get_collect_transport,
                'collector.clusters.': self._get_collect_cluster,
            }
            for _sec in _help:
                if self.opts.topic.startswith(_sec):
                    cls = _help[_sec]()
                    break
        return cls

    def _get_collect_transport(self):
        from sos.collector.sosnode import TRANSPORTS
        _transport = self.opts.topic.split('.')[-1]
        if _transport in TRANSPORTS:
            return TRANSPORTS[_transport]

    def _get_collect_cluster(self):
        from sos.collector import SoSCollector
        import sos.collector.clusters
        clusters = SoSCollector._load_modules(sos.collector.clusters,
                                              'clusters')
        for cluster in clusters:
            if cluster[0] == self.opts.topic.split('.')[-1]:
                return cluster[1]

    def _get_plugin_variant(self):
        mod = importlib.import_module('sos.' + self.opts.topic)
        self.load_local_policy()
        mems = inspect.getmembers(mod, inspect.isclass)
        plugins = [m[1] for m in mems if issubclass(m[1], Plugin)]
        for plugin in plugins:
            if plugin.__subclasses__():
                cls = self.policy.match_plugin(plugin.__subclasses__())
                return cls

    def _get_policy_by_name(self):
        _topic = self.opts.topic.split('.')[-1]
        # mimic policy loading to discover all policiy classes without
        # needing to manually define each here
        import sos.policies.distros
        _helper = ImporterHelper(sos.policies.distros)
        for mod in _helper.get_modules():
            for policy in import_policy(mod):
                _p = policy.__name__.lower().replace('policy', '')
                if _p == _topic:
                    return policy

    def display_self_help(self):
        """Displays the help information for this component directly, that is
        help for `sos help`.
        """
        self_help = HelpSection(
            'Detailed help for sos help',
            ('The \'help\' sub-command is used to provide more detailed '
             'information on different sub-commands available to sos as well '
             'as different components at play within those sub-commands.')
        )
        self_help.add_text(
            'SoS - officially pronounced "ess-oh-ess" - is a diagnostic and '
            'supportability utility used by several Linux distributions as an '
            'easy-to-use tool for standardized data collection. The most known'
            ' component of which is %s (formerly sosreport) which is used to '
            'collect troubleshooting information into an archive for review '
            'by sysadmins or technical support teams.'
            % bold('sos report')
        )

        subsect = self_help.add_section('How to search using sos help')
        usage = bold('$component.$topic.$subtopic')
        subsect.add_text(
            'To get more information on a given topic, use the form \'%s\'.'
            % usage
        )

        rep_ex = bold('sos help report.plugins.kernel')
        subsect.add_text("For example '%s' will provide more information on "
                         "the kernel plugin for the report function." % rep_ex)

        avail_help = self_help.add_section('Available Help Sections')
        avail_help.add_text(
            'The following help sections are available. Additional help'
            ' topics and subtopics may be displayed within their respective '
            'help section.\n'
        )

        sections = {
            'report':   'Detailed help on the report command',
            'report.plugins': 'Information on the plugin design of sos',
            'report.plugins.$plugin': 'Information on a specific $plugin',
            'clean':    'Detailed help on the clean command',
            'collect':  'Detailed help on the collect command',
            'policies': 'How sos operates on different distributions'
        }

        for sect in sections:
            avail_help.add_text(
                "\t{:<36}{}".format(bold(sect), sections[sect]),
                newline=False
            )

        self_help.display()


class HelpSection():
    """This class is used to build the output displayed by `sos help` in a
    standard fashion that provides easy formatting controls.
    """

    def __init__(self, title='', content='', indent=''):
        """
        :param title:   The title of the output section, will be prominently
                        displayed
        :type title:    ``str``

        :param content: The text content to be displayed with this section
        :type content:  ``str``

        :param indent:  If the section should be nested, set this to a multiple
                        of 4.
        :type indent:   ``int``
        """
        self.title = title
        self.content = content
        self.indent = indent
        self.sections = OrderedDict()

    def set_title(self, title):
        """Set or override the title for this help section

        :param title:   The name to set for this help section
        :type title:    ``str``
        """
        self.title = title

    def add_text(self, content, newline=True):
        """Add body text to this section. If content for this section already
        exists, append the new ``content`` after a newline.

        :param content:     The text to add to the section
        :type content:      ``str``
        """
        if self.content:
            ln = '\n\n' if newline else '\n'
            content = ln + content
        self.content += content

    def add_section(self, title, content='', indent=''):
        """Add a section of text to the help section that will be displayed
        when the HelpSection object is printed.

        Sections will be printed *in the order added*.

        This will return a subsection object with which block(s) of text may be
        added to the subsection associated with ``title``.

        :param title:   The title of the subsection being added
        :type title:    ``str``

        :param content: The text the new section should contain
        :type content:  ``str``

        :returns:   The newly created subsection for ``title``
        :rtype:     ``HelpSection``
        """
        self._add_section(title, content, indent)
        return self.sections[title]

    def _add_section(self, title, content='', indent=''):
        """Internal method used to add a new subsection to this help output

        :param title:   The title of the subsection being added
        :type title:    ``str`
        """
        if title in self.sections:
            raise Exception('A section with that title already exists')
        self.sections[title] = HelpSection(title, content, indent)

    def display(self):
        """Print the HelpSection contents, including any subsections, to
        console.
        """
        print(fill(
            bold(self.title), width=TERMSIZE, initial_indent=self.indent
        ))
        for ln in self.content.splitlines():
            print(fill(ln, width=TERMSIZE, initial_indent=self.indent))
        for section in self.sections:
            print('')
            self.sections[section].display()
