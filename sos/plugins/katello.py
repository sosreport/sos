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

class katello(sos.plugintools.PluginBase):
    """Katello project related information
    """

    def defaultenabled(self):
        return True

    def checkenabled(self):
        self.packages = ["katello", "katello-common", "katello-headpin"]
        self.files = ["/usr/bin/katello-debug"]
        return sos.plugintools.PluginBase.checkenabled(self)

    def setup(self):
        katello_debug = "/usr/bin/katello-debug"
        if os.path.isfile(katello_debug):
            katello_debug_path = os.path.join(self.cInfo['dstroot'],"katello-debug")
            self.collectExtOutput("%s --notar -d %s" % (katello_debug, katello_debug_path))
