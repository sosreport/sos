# Copyright (C) 2017 Red Hat, Inc., Marcus Linden <mlinden@redhat.com>
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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, \
    SuSEPlugin


class Conntrackd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, SuSEPlugin):
    """conntrackd - netfilter connection tracking user-space daemon
    """

    plugin_name = 'conntrackd'
    profiles = ('network', 'cluster')

    packages = ('conntrack-tools', 'conntrackd')

    def setup(self):
        self.add_copy_spec("/etc/conntrackd/conntrackd.conf")
        self.add_cmd_output([
            "conntrackd -s network",
            "conntrackd -s cache",
            "conntrackd -s runtime",
            "conntrackd -s link",
            "conntrackd -s rsqueue",
            "conntrackd -s queue",
            "conntrackd -s ct",
            "conntrackd -s expect",
        ])

# vim: set et ts=4 sw=4 :
