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
import os

class foreman(sos.plugintools.PluginBase):
    """Foreman related information
    """
    packages = [ 'foreman' ]

    def setup(self):
        foreman_debug_path = os.path.join(self.cInfo['cmddir'],
                                'foreman', 'foreman-debug')
        try:
            os.makedirs(foreman_debug_path)
        except:
            return
 
        self.collectExtOutput("/usr/sbin/foreman-debug -a -d %s"
                              % foreman_debug_path)
        return
