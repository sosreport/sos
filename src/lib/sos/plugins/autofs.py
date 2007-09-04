## Copyright (C) 2007 Red Hat, Inc., Adam Stokes <astokes@redhat.com>

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

class autofs(sos.plugintools.PluginBase):
    """autofs server-related information
    """
    def checkenabled(self):
        if self.cInfo["policy"].runlevelDefault() in self.cInfo["policy"].runlevelByService("autofs"):
            return True
        return False

    def checkdebug(self):
        """ 
        Probably not needed? I think we can pretty much assume that if daemon.* is
        set in /etc/syslog.conf then debugging is enabled.
        FIXME: remove checkdebug if not needed in future release
        """
        pass
        # Global debugging
        optlist=[]
        opt = self.doRegexFindAll(r"^(DEFAULT_LOGGING|DAEMONOPTIONS)=(.*)", "/etc/sysconfig/autofs")
        for opt1 in opt:
            optlist.append(opt1)[1]
        for dtest in optlist:
            if dtest == "--debug" or dtest == "debug":
                return True

    def getdaemondebug(self):
        """ capture daemon debug output
        """
        debugout=self.doRegexFindAll(r"^daemon.*\s+(\/var.*)", "/etc/syslog.conf")
        for i in debugout:
            return i

    def setup(self):
        self.addCopySpec("/etc/auto*")
        self.addCopySpec("/etc/sysconfig/autofs")
        self.addCopySpec("/etc/rc.d/init.d/autofs")
        self.collectExtOutput("service autofs status")

        # if debugging to file is enabled, grab that file too
        daemon_debug_file = self.getdaemondebug()
        if daemon_debug_file:
            self.addCopySpec(daemon_debug_file)
        return

