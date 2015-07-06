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


class Cgroups(Plugin, DebianPlugin, UbuntuPlugin):
    """Control groups subsystem
    """

    plugin_name = "cgroups"
    profiles = ('system',)
    files = ('/proc/cgroups',)

    def setup(self):
        self.add_copy_spec([
            "/proc/cgroups",
            "/sys/fs/cgroup"
        ])
        return


class RedHatCgroups(Cgroups, RedHatPlugin):

    def setup(self):
        super(RedHatCgroups, self).setup()
        self.add_copy_spec([
            "/etc/sysconfig/cgconfig",
            "/etc/sysconfig/cgred",
            "/etc/cgsnapshot_blacklist.conf",
            "/etc/cgconfig.conf",
            "/etc/cgrules.conf"
        ])

# vim: set et ts=4 sw=4 :
