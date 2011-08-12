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

class yum(sos.plugintools.PluginBase):
    """yum information
    """

    optionList = [("yumlist", "list repositories and packages", "slow", False),
                  ("yumdebug", "gather yum debugging data", "slow", False)]

    def checkenabled(self):
        self.files = [ "/etc/yum.conf" ]
        self.packages = [ "yum" ]
        return sos.plugintools.PluginBase.checkenabled(self)

    def analyze(self):
        # repo sanity checking
        # TODO: elaborate/validate actual repo files, however this directory should
        # be empty on RHEL 5+ systems.
        if self.policy().rhelVersion() == 5:
            if len(os.listdir("/etc/yum.repos.d/")):
                self.addAlert("/etc/yum.repos.d/ contains additional repository "+
                                 "information and can cause rpm conflicts.")

    def setup(self):
        # Pull all yum related information
        self.addCopySpec("/etc/yum")
        self.addCopySpec("/etc/yum.repos.d")
        self.addCopySpec("/etc/yum.conf")
        self.addCopySpec("/var/log/yum.log")

        # Get a list of channels the machine is subscribed to.
        self.collectExtOutput("yum -C repolist")

        if self.getOption("yumlist"):
            # List various information about available packages
            self.collectExtOutput("/usr/bin/yum list")

        if self.getOption("yumdebug") and self.isInstalled('yum-utils'):
            ret, output, rtime = self.callExtProg("/usr/bin/yum-debug-dump")
            try:
                self.collectExtOutput("/bin/zcat %s" % (output.split()[-1],))
            except IndexError:
                pass
        return
