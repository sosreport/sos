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

from sos.plugins import Plugin, DebianPlugin, UbuntuPlugin


class Dpkg(Plugin, DebianPlugin, UbuntuPlugin):
    """Debian Package Management
    """

    plugin_name = 'dpkg'
    profiles = ('sysmgmt', 'packagemanager')

    def setup(self):
        self.add_cmd_output("dpkg -l", root_symlink="installed-debs")
        if self.get_option("verify"):
            self.add_cmd_output("dpkg -V")
            self.add_cmd_output("dpkg -C")
        self.add_copy_spec([
            "/var/cache/debconf/config.dat",
            "/etc/debconf.conf"
        ])
        if not self.get_option("all_logs"):
            limit = self.get_option("log_size")
            self.add_copy_spec_limit("/var/log/dpkg.log",
                                     sizelimit=limit)
        else:
            self.add_copy_spec("/var/log/dpkg.log*")

# vim: set et ts=4 sw=4 :
