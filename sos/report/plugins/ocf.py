# Copyright (C) 2026
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Ocf(Plugin, IndependentPlugin):
    """Archive OCF resource agent scripts and libraries.

    Collects the standard OCF root under /usr/lib/ocf used by Pacemaker
    resource agents, including resource agent scripts under resource.d/
    and shared libraries/support scripts under lib/heartbeat/.
    """

    short_desc = 'OCF resource agent scripts and libraries'

    plugin_name = 'ocf'
    profiles = ('cluster',)
    packages = ('resource-agents', 'resource-agents-base')
    files = ('/usr/lib/ocf',)

    def setup(self):
        self.add_file_tags({
            '/usr/lib/ocf/lib/heartbeat/ocf-binaries': 'ocf_binaries',
            '/usr/lib/ocf/lib/heartbeat/ocf-shellfuncs': 'ocf_shellfuncs',
        })

        self.add_copy_spec('/usr/lib/ocf')

    def postproc(self):
        # password=secret -> password=********
        self.do_path_regex_sub(
            r"/usr/lib/ocf/.*",
            r"(passw([^\s=]*)=)\S+",
            r"\1********"
        )
        # api_key=abc123 -> api_key=********
        self.do_path_regex_sub(
            r"/usr/lib/ocf/.*",
            r"(api[_]?key[^\s=]*)=\S+",
            r"\1=********"
        )

# vim: set et ts=4 sw=4 :
