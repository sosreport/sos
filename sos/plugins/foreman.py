## Copyright (C) 2013 Red Hat, Inc., Lukas Zapletal <lzap@redhat.com>

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

class foreman(sos.plugintools.PluginBase):
    """Foreman project related information
    """

    def defaultenabled(self):
        return True

    def checkenabled(self):
        self.packages = ["foreman"]
        self.files = ["/usr/sbin/foreman-debug"]
        return sos.plugintools.PluginBase.checkenabled(self)

    def setup(self):
        foreman_debug = "/usr/sbin/foreman-debug"
        if os.path.isfile(foreman_debug):
            foreman_debug_path = os.path.join(self.cInfo['dstroot'],"foreman-debug")
            self.collectExtOutput("%s -a -d %s" % (foreman_debug, foreman_debug_path))
