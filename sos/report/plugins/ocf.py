# Copyright (C) 2026
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin)


class Ocf(Plugin):
    """Archive OCF resource agent binaries and libraries.

    Collects OCF installation paths used by Pacemaker resource agents,
    including helper binaries under /usr/bin/ocf and the standard OCF root
    hierarchy under /usr/lib/ocf (resource agents, shared libraries, and
    support scripts).
    """

    short_desc = 'OCF resource agent binaries and libraries'

    plugin_name = 'ocf'
    profiles = ('cluster',)
    packages = ('resource-agents', 'resource-agents-base')
    files = ('/usr/lib/ocf', '/usr/bin/ocf')

    ocf_paths = (
        '/usr/bin/ocf',
        '/usr/lib/ocf',
    )

    def setup(self):
        specs = []
        for path in self.ocf_paths:
            if self.path_exists(path):
                specs.append(path)

        if not specs:
            return

        self.add_file_tags({
            '/usr/lib/ocf/lib/heartbeat/ocf-binaries': 'ocf_binaries',
            '/usr/lib/ocf/lib/heartbeat/ocf-shellfuncs': 'ocf_shellfuncs',
        })

        self.add_copy_spec(specs)
        self.add_dir_listing(specs)

    def setup_rpm_inventory(self):
        self.add_cmd_output(
            'sh -c "rpm -ql resource-agents resource-agents-base 2>/dev/null '
            '| grep /ocf"'
        )

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
        self.do_path_regex_sub(
            r"/usr/bin/ocf/.*",
            r"(passw([^\s=]*)=)\S+",
            r"\1********"
        )


class RedHatOcf(Ocf, RedHatPlugin):
    def setup(self):
        self.setup_rpm_inventory()
        super().setup()


class DebianOcf(Ocf, DebianPlugin, UbuntuPlugin):
    """ Parent class Ocf setup() will be called """

# vim: set et ts=4 sw=4 :
