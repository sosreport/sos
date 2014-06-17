## Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
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

import sos.plugintools

class ctdb(sos.plugintools.PluginBase):
    """Samba CTDB related information
    """
    packages = ('ctdb',)

    def setup(self):
        self.addCopySpec("/etc/sysconfig/ctdb")
        self.addCopySpec("/etc/ctdb/public_addresses")
        self.addCopySpec("/etc/ctdb/static-routes")
        self.addCopySpec("/etc/ctdb/multipathd")
        self.addCopySpec("/var/log/log.ctdb")

        self.collectExtOutput("ctdb ip")
        self.collectExtOutput("ctdb ping")
        self.collectExtOutput("ctdb status")
        self.collectExtOutput("ctdb ifaces")
        self.collectExtOutput("ctdb listnodes")
        self.collectExtOutput("ctdb listvars")
        self.collectExtOutput("ctdb statistics")
        self.collectExtOutput("ctdb getdbmap")


# vim: et ts=4 sw=4
