## Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

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

class systemtap(Plugin, RedHatPlugin):
    """SystemTap information
    """
    def checkenabled(self):
        self.files = [ "/usr/bin/stap" ]
        self.packages = [ "systemtap", "systemtap-runtime" ]
        return Plugin.checkenabled(self)

    def setup(self):
        self.collectExtOutput("/usr/bin/stap -V 2")
        self.collectExtOutput("/bin/uname -r")
