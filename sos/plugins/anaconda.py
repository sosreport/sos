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

class anaconda(sos.plugintools.PluginBase):
    """Anaconda / Installation information
    """
    def checkenabled(self):
        if os.path.exists("/var/log/anaconda.log"):
            return True
        return False

    def setup(self):
        self.addCopySpec("/root/anaconda-ks.cfg")
        self.addCopySpec("/root/install.log")
        self.addCopySpec("/root/install.log.syslog")
        self.addCopySpec("/var/log/anaconda.log")
        self.addCopySpec("/var/log/anaconda.syslog")
        self.addCopySpec("/var/log/anaconda.xlog")
        return

    def postproc(self):
        self.doRegexSub("/root/anaconda-ks.cfg", r"(\s*rootpw\s*).*", r"\1*** PASSWORD ELIDED ***")
        return
