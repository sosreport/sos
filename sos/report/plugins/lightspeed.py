# Copyright (C) 2025 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class Lightspeed(Plugin, RedHatPlugin):

    short_desc = 'Lightspeed Command Line Assistant'

    plugin_name = 'lightspeed'
    profiles = ('ai',)
    services = ('clad',)

    option_list = [
        PluginOpt('historydb', default=False,
                  desc='collect the history database')
    ]

    config_file = "/etc/xdg/command-line-assistant/config.toml"

    def setup(self):
        self.add_copy_spec([
            self.config_file,
            "/etc/systemd/system/clad.service.d/"
        ])

        if self.get_option('historydb'):
            self.add_copy_spec(
                    "/var/lib/command-line-assistant/history.db",
            )

    def postproc(self):
        self.do_path_regex_sub(self.config_file,
                               r"(password\s+=\s+)(\S+)",
                               r"\1********\n")

# vim: set et ts=4 sw=4 :
