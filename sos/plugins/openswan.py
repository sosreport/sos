# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Openswan(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Openswan IPsec
    """

    plugin_name = 'openswan'
    profiles = ('network', 'security')
    option_list = [
        ("ipsec-barf", "collect the output of the ipsec barf command",
         "slow", False)
    ]

    files = ('/etc/ipsec.conf',)
    packages = ('openswan', 'libreswan')

    def setup(self):
        self.add_copy_spec([
            "/etc/ipsec.conf",
            "/etc/ipsec.d"
        ])

        # although this is 'verification' it's normally a very quick
        # operation so is not conditional on --verify
        self.add_cmd_output("ipsec verify")
        if self.get_option("ipsec-barf"):
            self.add_cmd_output("ipsec barf")

        self.add_forbidden_path([
            '/etc/ipsec.secrets',
            '/etc/ipsec.secrets.d/*',
            '/etc/ipsec.d/*.db',
            '/etc/ipsec.d/*.secrets'
        ])

# vim: set et ts=4 sw=4 :
