# Copyright (C) 2022 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Fapolicyd(Plugin, RedHatPlugin):

    """
    This plugin collects configuration and some probes of Fapolicyd software
    framework.
    """
    short_desc = 'Fapolicyd framework'

    plugin_name = "fapolicyd"
    packages = ("fapolicyd", )

    def setup(self):
        self.add_copy_spec([
            "/etc/fapolicyd/fapolicyd.conf",
            "/etc/fapolicyd/compiled.rules",
            "/etc/fapolicyd/fapolicyd.trust",
            "/etc/fapolicyd/rules.d/",
            "/etc/fapolicyd/trust.d/",
            "/var/log/fapolicyd-access.log",
        ])

        self.add_cmd_output([
            "fapolicyd-cli --list",
            "fapolicyd-cli --check-config",
            "fapolicyd-cli --check-trustdb",
            "fapolicyd-cli --check-path",
            "fapolicyd-cli --check-status",
            "fapolicyd-cli --check-watch_fs",
        ])


# vim: set et ts=4 sw=4 :
