## Copyright (C) 2011, 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Infiniband(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Infiniband related information
    """

    plugin_name = 'infiniband'

    def check_enabled(self):
         if self.commons["policy"].pkg_by_name("libibverbs-utils"):
             return True
         return False

    def setup(self):
        self.add_copy_specs([
            "/etc/ofed/openib.conf",
            "/etc/ofed/opensm.conf"])

        self.add_cmd_output("ibv_devices")
        self.add_cmd_output("ibv_devinfo")
        self.add_cmd_output("ibstat")
        self.add_cmd_output("ibstatus")
        self.add_cmd_output("ibhosts")

        return
