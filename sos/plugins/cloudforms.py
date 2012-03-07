## Copyright (C) 2012 Red Hat Inc., Bryn M. Reeves <bmr@redhat.com>
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

class cloudforms(sos.plugintools.PluginBase):
    """CloudForms related information
    """

    def defaultenabled(self):
        return False

    def checkenabled(self):
        # enable if any related package is installed
        self.packages = ["katello"]
        return sos.plugintools.PluginBase.checkenabled(self)

    def setup(self):
        self.collectExtOutput("/usr/share/katello/scripts/katello-debug -d %s" \
            % os.path.join(self.cInfo['dstroot'],"cloudforms"))
