# Copyright (C) 2024 Marcin Wilk <marcin.wilk@canonical.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Telegraf(Plugin, IndependentPlugin):

    short_desc = 'Telegraf, the metric collecting tool, plugin'

    plugin_name = "telegraf"
    profiles = ('observability',)
    services = ('telegraf',)
    files = (
        '/etc/telegraf/',
        '/etc/default/telegraf',
    )

    def setup(self):
        # Collect data from 'files' var
        super().setup()

        # collect logs in addition to the above
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/telegraf/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/telegraf/*.log",
            ])

    def postproc(self):
        protect_keys = [
            "password",
            "token",
            "pwd",
        ]
        telegraf_path_exps = [
            "/etc/telegraf/*",
            "/etc/default/telegraf",
        ]
        match_exp = fr"(^\s*(.*({'|'.join(protect_keys)}))\s*=\s*)(.*)"

        # Obfuscate passwords and keys
        self.do_path_regex_sub(fr"({'|'.join(telegraf_path_exps)})",
                               match_exp,
                               r"\1*********")

        # Obfuscate certs
        self.do_file_private_sub(telegraf_path_exps[0])


# vim: et ts=4 sw=4
