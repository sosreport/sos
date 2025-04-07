# Copyright (C) 2025 Red Hat, Inc., David Wolstromer <dwolstro@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Valkey(Plugin, IndependentPlugin):

    short_desc = 'Valkey, in-memory data structure store'

    plugin_name = 'valkey'
    profiles = ('services',)

    packages = ('valkey',)

    var_puppet_gen = "/var/lib/config-data/puppet-generated/valkey"

    def setup(self):
        self.add_copy_spec([
            "/etc/valkey/*",
            self.var_puppet_gen + "/etc/valkey*",
            self.var_puppet_gen + "/etc/valkey/",
            self.var_puppet_gen + "/etc/security/limits.d/"
        ])

        self.add_cmd_output("valkey-cli info")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/valkey/valkey.log*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/valkey/valkey.log",
            ])

    def postproc(self):
        for path in ["/etc/valkey/", self.var_puppet_gen + "/etc/valkey"]:
            self.do_file_sub(
                path + "valkey.conf",
                r"(primaryauth|requirepass|key-file-pass)\s.*",
                r"\1 ********"
            )
            self.do_file_sub(
                path + "sentinel.conf",
                r"(primaryauth|requirepass|key-file-pass)\s.*",
                r"\1 ********"
            )

# vim: set et ts=4 sw=4 :
