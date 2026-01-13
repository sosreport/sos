# Copyright (C) 2026 Canonical Ltd.,
# Leah Goldberg <leah.goldberg@canonical.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Graylog(Plugin, IndependentPlugin):
    """
    Collects diagnostic information for Graylog Server.
    """

    short_desc = "Graylog centralized logging server"

    plugin_name = "graylog"
    profiles = ("security",)
    packages = ("graylog-datanode", "graylog-server", "graylog-enterprise",)
    services = ("graylog-server",)

    def setup(self):
        self.add_copy_spec([
            "/etc/graylog",
            "/var/lib/graylog-server/journal",
        ])

    def postproc(self):
        # Obfuscate secrets in Graylog config files
        self.do_path_regex_sub(
            r"/etc/graylog/.*\.conf$",
            r"(?i)^(\s*[^#\n]*(password|secret|token|key|_sha\d*)\s*=\s*).*$",
            r"\1******"
        )

        # Obfuscate credentials embedded in URLs (user:password@host)
        self.do_cmd_output_sub(
            "systemctl status graylog-server",
            r"(://)[^:@/\s]+:[^@/\s]+@",
            r"\1******:******@"
        )

# vim: set et ts=4 sw=4 :
