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
import commands
from os.path import normpath, join, exists

class named(Plugin, RedHatPlugin):
    """named related information
    """

    files = ('/etc/named.conf', '/etc/sysconfig/named')
    packages = ('bind')

    def getDnsDir(self, configFile):
        """ grab directory path from named{conf,boot}
        """
        directoryList = self.doRegexFindAll("directory\s+\"(.*)\"", configFile)
        return normpath(directoryList[0])

    def setup(self):
        cfgFiles = ("/etc/named.conf",
                    "/etc/named.boot")
        for cfg in cfgFiles:
            if exists(cfg):
                self.addCopySpec(cfg)
                self.addCopySpec(self.getDnsDir(cfg))
                self.addForbiddenPath(join(self.getDnsDir(cfg),"chroot/dev"))
                self.addForbiddenPath(join(self.getDnsDir(cfg),"chroot/proc"))
        self.addCopySpec("/etc/sysconfig/named")
