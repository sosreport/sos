# Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>
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

from sos.plugins import Plugin, UbuntuPlugin


class Apparmor(Plugin, UbuntuPlugin):
    """Apparmor mandatory access control
    """

    plugin_name = 'apparmor'
    profiles = ('security',)

    def setup(self):
        self.add_copy_spec([
            "/etc/apparmor*"
        ])
        self.add_forbidden_path("/etc/apparmor.d/cache")
        self.add_forbidden_path("/etc/apparmor.d/libvirt/libvirt*")
        self.add_forbidden_path("/etc/apparmor.d/abstractions")
        self.add_cmd_output([
            "apparmor_status",
            "ls -alh /etc/apparmor.d/abstractions",
            "ls -alh /etc/apparmor.d/libvirt",
        ])

# vim: set et ts=4 sw=4 :
