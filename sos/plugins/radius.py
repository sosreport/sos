## Copyright (C) 2007 Navid Sheikhol-Eslami <navid@redhat.com>

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
from os.path import exists

class radius(Plugin):
    """radius related information
    """

    plugin_name = "radius"
    packages = ('freeradius',)

class RedHatRadius(radius, RedHatPlugin):
    """radius related information on Red Hat distributions
    """

    files = ('/etc/raddb',)

    def setup(self):
        super(RedHatRadius, self).setup()
        self.addCopySpecs(["/etc/raddb", "/etc/pam.d/radiusd", "/var/log/radius"])

    def postproc(self):
        self.doFileSub("/etc/raddb/sql.conf", r"(\s*password\s*=\s*)\S+", r"\1***")

class DebianRadius(radius, DebianPlugin, UbuntuPlugin):
    """radius related information on Debian distributions
    """

    files = ('/etc/freeradius',)

    def setup(self):
        super(DebianRadius, self).setup()
        self.addCopySpecs(["/etc/freeradius",
                           "/etc/pam.d/radiusd",
                           "/etc/default/freeradius",
                           "/var/log/freeradius"])
