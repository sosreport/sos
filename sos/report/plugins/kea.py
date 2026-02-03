# Copyright (C) 2024 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, IndependentPlugin)


class Kea(Plugin, IndependentPlugin):
    """
    Kea is the next generation of DHCP software, developed by Internet
    Systems Consortium (ISC). It supports both the DHCPv4 and DHCPv6 protocols
    along with their extensions, e.g. prefix delegation and dynamic updates to
    DNS.
    """
    short_desc = 'Kea DHCP and DDNS server from ISC'

    plugin_name = "kea"
    packages = ("kea", "kea-common",
                "isc-kea", "kea-dhcp4-server",
                "kea-dhcp6-server",)
    services = ('kea-ctrl-agent', 'kea-dhcp-ddns',
                'kea-dhcp4', 'kea-dhcp6',)

    def setup(self):
        self.add_forbidden_path("/etc/kea/kea-api-password")
        self.add_copy_spec([
            "/etc/kea/*",
        ])
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/kea/kea*.log*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/kea/kea*.log",
            ])
        self.add_cmd_output([
            "keactrl status",
        ])

    def postproc(self):
        """ format is "password": "kea", """
        self.do_path_regex_sub(
            '/etc/kea/*',
            r'(^\s*"password":\s*)(".*"),',
            r'\1********'
        )

# vim: set et ts=4 sw=4 :
