# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class Dhcp(Plugin):
    """DHCP daemon
    """

    plugin_name = "dhcp"
    profiles = ('network',)


class RedHatDhcp(Dhcp, RedHatPlugin):

    files = ('/etc/rc.d/init.d/dhcpd',)
    packages = ('dhcp',)

    def setup(self):
        super(RedHatDhcp, self).setup()
        self.add_copy_spec([
            "/etc/dhcpd.conf",
            "/etc/dhcp"
        ])


class UbuntuDhcp(Dhcp, UbuntuPlugin):

    files = ('/etc/init.d/udhcpd',)
    packages = ('udhcpd',)

    def setup(self):
        super(UbuntuDhcp, self).setup()
        self.add_copy_spec([
            "/etc/default/udhcpd",
            "/etc/udhcpd.conf"
        ])

# vim: set et ts=4 sw=4 :
