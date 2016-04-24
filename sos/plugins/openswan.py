# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Openswan(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Openswan IPsec
    """

    plugin_name = 'openswan'
    profiles = ('network', 'security')
    option_list = [("ipsec-barf",
                    "collect the output of the ipsec barf command",
                    "slow", False)]

    files = ('/etc/ipsec.conf',)
    packages = ('openswan',)

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

# vim: set et ts=4 sw=4 :
