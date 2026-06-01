# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Dhcp(Plugin):

    short_desc = 'DHCP daemon'

    plugin_name = "dhcp"
    profiles = ('network',)


class RedHatDhcp(Dhcp, RedHatPlugin):

    packages = ('dhcp', 'dhcp-server',)

    def setup(self):
        super().setup()
        self.add_copy_spec([
            "/etc/dhcpd.conf",
            "/etc/dhcp"
        ])


class DebianDhcp(Dhcp, DebianPlugin, UbuntuPlugin):

    files = ('/etc/init.d/udhcpd',)
    packages = ('udhcpd', 'isc-dhcp-server', 'dnsmasq')

    def setup(self):
        super().setup()
        self.add_copy_spec([

            # udhcpd
            "/etc/default/udhcpd",
            "/etc/udhcpd.conf",

            # ISC DHCP server
            "/etc/dhcp",
            "/etc/default/isc-dhcp-server",
            "/var/lib/dhcp",

            # dnsmasq
            "/etc/dnsmasq.conf",
            "/etc/dnsmasq.d",
            "/etc/default/dnsmasq",
        ])

        self.add_cmd_output([
            # ISC DHCP server
            "systemctl --full status isc-dhcp-server",
            "dhcp-lease-list",

            # dnsmasq
            "systemctl --full status dnsmasq",
            "dnsmasq --test",
        ])

# vim: set et ts=4 sw=4 :
