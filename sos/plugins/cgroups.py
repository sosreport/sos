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

class cgroups(Plugin, DebianPlugin, UbuntuPlugin):
    """cgroup subsystem information
    """

    plugin_name = "cgroups"

    files = ('/proc/cgroups',)

    def setup(self):
        self.addCopySpecs(["/proc/cgroups",
                           "/sys/fs/cgroup"])
        return

class RedHatCgroups(cgroups, RedHatPlugin):
    """Red Hat specific cgroup subsystem information
    """

    def setup(self):
        self.addCopySpecs(["/etc/sysconfig/cgconfig",
                           "/etc/sysconfig/cgred.conf",
                           "/etc/cgsnapshot_blacklist.conf",
                           "/etc/cgconfig.conf",
                           "/etc/cgrules.conf"])
        cgroups.setup(self)

