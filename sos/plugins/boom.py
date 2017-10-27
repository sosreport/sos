# Copyright (C) 2017 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
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

from sos.plugins import Plugin, RedHatPlugin


class Boom(Plugin, RedHatPlugin):
    """Configuration data for the boom boot manager.
    """

    plugin_name = 'boom'
    profiles = ('boot', 'system')

    packages = ('python-boom', 'python2-boom', 'python3-boom')

    def setup(self):
        self.add_copy_spec([
            "/boot/boom/profiles",
            "/boot/loader/entries",
            "/etc/default/boom",
            "/etc/grub.d/42_boom"
        ])

        self.add_cmd_output([
            "boom list -VV",
            "boom profile list -VV"
        ])

# vim: set et ts=4 sw=4 :
