# Copyright (C) 2015 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

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


class LightDm(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Light Display Manager
    """
    packages = ('lightdm', )
    profiles = ('desktop', )
    plugin_name = 'lightdm'

    def setup(self):
        self.add_cmd_output([
            "journalctl -u lightdm",
            "systemctl status lightdm.service"
        ])
        self.add_copy_spec([
            "/etc/lightdm/lightdm.conf",
            "/etc/lightdm/users.conf"
        ])
        if not self.get_option("all_logs"):
            limit = self.get_option("log_size")
            self.add_copy_spec_limit("/var/log/lightdm/lightdm.log",
                                     sizelimit=limit)
            self.add_copy_spec_limit("/var/log/lightdm/x-0-greeter.log",
                                     sizelimit=limit)
            self.add_copy_spec_limit("/var/log/lightdm/x-0.log",
                                     sizelimit=limit)
        else:
            self.add_copy_spec("/var/log/lightdm")

# vim: set et ts=4 sw=4 :
