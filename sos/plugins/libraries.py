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

class libraries(sos.plugintools.PluginBase):
    """information on shared libraries
    """

    optionList = [('ldconfigv', 'the name of each directory as it is scanned, and any links that are created.', 
                    "slow", False)]

    def setup(self):
        self.addCopySpec("/etc/ld.so.conf")
        self.addCopySpec("/etc/ld.so.conf.d")
        if self.getOption("ldconfigv"):
            self.collectExtOutput("/sbin/ldconfig -v -N -X")
        self.collectExtOutput("/sbin/ldconfig -p -N -X")
        return

