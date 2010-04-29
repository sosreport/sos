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

import os
import sos.plugintools
import glob
import socket

class sanitize(sos.plugintools.PluginBase):
    """ sanitize specified log files, etc
    """
    hostname = socket.gethostname()

    def defaultenabled(self):
        # disabled by default b/c still a work in progress
        return False

    def setup(self):
        # sanitize ip's, hostnames in logs
        rhelver = self.policy().rhelVersion()
        if rhelver == 5 or rhelver == 4:
            logs=self.doRegexFindAll(r"^\S+\s+(\/.*log.*)\s+$", "/etc/syslog.conf")
        else:
            logs=self.doRegexFindAll(r"^\S+\s+(\/.*log.*)\s+$", "/etc/rsyslog.conf")
        for log in logs:
            self.addCopySpec(log)

    def postproc(self):
        self.doRegexSub('/var/log/messages', r"(%s|localhost)" % (self.hostname,), r"sanitized-hostname")
        self.doRegexSub('/var/log/messages', r"([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})", r"sanitized-ip")

