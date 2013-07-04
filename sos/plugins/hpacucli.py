## hpacucli.py
## Captures HP Smart Array specific information during a sos run.

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

class hpacucli(sos.plugintools.PluginBase):
    """HP SmartArray related information
    """
    def checkenabled(self):
        if os.path.exists("/usr/sbin/hpacucli"):
            return True
        return False
 
    def setup(self):
        path = os.path.join(self.cInfo['cmddir'], "hpacucli")
        if not os.path.exists(path):
            os.makedirs(path)
        filename = "hpacucli-diag.zip"
        filepath = os.path.join(path, filename)
        self.callExtProg("/usr/sbin/hpacucli ctrl all diag file=" + filepath)
        self.collectExtOutput("/usr/sbin/hpacucli ctrl all show")
        self.collectExtOutput("/usr/sbin/hpacucli ctrl all show status")
        self.collectExtOutput("/usr/sbin/hpacucli ctrl all show detail")
        return
