## Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>

## This program is free software; you can redistribute it and/or modify
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

import sos.plugintools
import os

class ds(sos.plugintools.PluginBase):
    """Directory Server information
    """

    def check_version(self):
        if self.isInstalled("redhat-ds-base") or \
        os.path.exists("/etc/dirsrv"):
            return "ds8"
        elif self.isInstalled("redhat-ds-7") or \
        os.path.exists("/opt/redhat-ds"):
            return "ds7"
        return False

    def checkenabled(self):
        if self.isInstalled("redhat-ds-base") or \
        os.path.exists("/etc/dirsrv"):
            return True
        elif self.isInstalled("redhat-ds-7") or \
        os.path.exists("/opt/redhat-ds"):
            return True
        return False

    def setup(self):
        if not self.check_version():
            self.addAlert("Directory Server not found.")
        elif "ds8" in self.check_version():
            self.addCopySpec("/etc/dirsrv/slapd*")
            self.addCopySpec("/var/log/dirsrv/*")
        elif "ds7" in self.check_version():
            self.addCopySpec("/opt/redhat-ds/slapd-*/config")
            self.addCopySpec("/opt/redhat-ds/slapd-*/logs")
        return

