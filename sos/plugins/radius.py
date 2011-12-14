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

from sos.plugins import Plugin, RedHatPlugin
from os.path import exists

class radius(Plugin, RedHatPlugin):
    """radius related information
    """
    def checkenabled(self):
        return self.isInstalled("freeradius") or exists("/etc/raddb")

    def setup(self):
        self.addCopySpecs(["/etc/raddb", "/etc/pam.d/radiusd", "/var/log/radius"])

    def postproc(self):
        self.doRegexSub("/etc/raddb/sql.conf", r"(\s*password\s*=\s*)\S+", r"\1***")
