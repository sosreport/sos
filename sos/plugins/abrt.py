# Copyright (C) 2010 Red Hat, Inc., Tomas Smetana <tsmetana@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Abrt(Plugin, RedHatPlugin):
    """Automatic Bug Reporting Tool
    """

    plugin_name = "abrt"
    profiles = ('system', 'debug')
    packages = ('abrt-cli', 'abrt-gui', 'abrt')
    files = ('/var/spool/abrt',)

    option_list = [
        ("detailed", 'collect detailed info for every report', 'slow', False)
    ]

    def info_detailed(self, list_file):
        for line in open(list_file).read().splitlines():
            if line.startswith("Directory:"):
                self.add_cmd_output("abrt-cli info -d '%s'" % line.split()[1])

    def setup(self):
        self.add_cmd_output("abrt-cli status")
        list_file = self.get_cmd_output_now("abrt-cli list")
        if self.get_option('detailed') and list_file:
            self.info_detailed(list_file)

        self.add_copy_spec([
            "/etc/abrt/abrt.conf",
            "/etc/abrt/abrt-action-save-package-data.conf",
            "/etc/abrt/plugins"
        ])
# vim: set et ts=4 sw=4 :
