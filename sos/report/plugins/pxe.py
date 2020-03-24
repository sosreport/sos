# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Pxe(Plugin):
    """PXE service
    """
    plugin_name = "pxe"
    profiles = ('sysmgmt', 'network')
    option_list = [("tftpboot", 'gathers content from the tftpboot path',
                    'slow', False)]


class RedHatPxe(Pxe, RedHatPlugin):

    files = ('/usr/sbin/pxeos',)
    packages = ('system-config-netboot-cmd',)

    def setup(self):
        super(RedHatPxe, self).setup()
        self.add_cmd_output("/usr/sbin/pxeos -l")
        self.add_copy_spec("/etc/dhcpd.conf")
        if self.get_option("tftpboot"):
            self.add_copy_spec("/tftpboot")


class DebianPxe(Pxe, DebianPlugin, UbuntuPlugin):

    packages = ('tftpd-hpa',)

    def setup(self):
        super(DebianPxe, self).setup()
        self.add_copy_spec([
            "/etc/dhcp/dhcpd.conf",
            "/etc/default/tftpd-hpa"
        ])
        if self.get_option("tftpboot"):
            self.add_copy_spec("/var/lib/tftpboot")

# vim: set et ts=4 sw=4 :
