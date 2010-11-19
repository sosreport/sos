## Copyright (C) 2007-2010 Red Hat, Inc., Kent Lamb <klamb@redhat.com>
##                                        Marc Sauton <msauton@redhat.com>
##                                        Pierre Carrier <pcarrier@redhat.com>

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
from os.path import exists
import glob

class cs(sos.plugintools.PluginBase):
    """Red Hat Certificate System 7.1, 7.3, 8.0 and dogtag related information
    """

    def checkversion(self):
        if self.isInstalled("redhat-cs") or exists("/opt/redhat-cs"):
            return 71
        elif self.isInstalled("rhpki-common") or len(glob.glob("/var/lib/rhpki-*")):
            return 73
        # 8 should cover dogtag
        elif self.isInstalled("pki-common") or exists("/usr/share/java/pki"):
            return 8
        return False

    def checkenabled(self):
        if self.isInstalled("redhat-cs") or \
           self.isInstalled("rhpki-common") or \
           self.isInstalled("pki-common") or \
           exists("/opt/redhat-cs") or \
           exists("/usr/share/java/rhpki") or \
           exists("/usr/share/java/pki"):
            return True
        return False

    def setup(self):
        csversion = self.checkversion()
        if not csversion:
            self.addAlert("Red Hat Certificate System not found.")
            return
        if csversion == 71:
            self.addCopySpec("/opt/redhat-cs/slapd-*/logs/access")
            self.addCopySpec("/opt/redhat-cs/slapd-*/logs/errors")
            self.addCopySpec("/opt/redhat-cs/slapd-*/config/dse.ldif")
            self.addCopySpec("/opt/redhat-cs/cert-*/errors")
            self.addCopySpec("/opt/redhat-cs/cert-*/config/CS.cfg")
            self.addCopySpec("/opt/redhat-cs/cert-*/access")
            self.addCopySpec("/opt/redhat-cs/cert-*/errors")
            self.addCopySpec("/opt/redhat-cs/cert-*/system")
            self.addCopySpec("/opt/redhat-cs/cert-*/transactions")
            self.addCopySpec("/opt/redhat-cs/cert-*/debug")
            self.addCopySpec("/opt/redhat-cs/cert-*/tps-debug.log")
        if csversion == 73:
            self.addCopySpec("/var/lib/rhpki-*/conf/*cfg*")
            self.addCopySpec("/var/lib/rhpki-*/conf/*.ldif")
            self.addCopySpec("/var/lib/rhpki-*/logs/debug")
            self.addCopySpec("/var/lib/rhpki-*/logs/catalina.*")
            self.addCopySpec("/var/lib/rhpki-*/logs/ra-debug.log")
            self.addCopySpec("/var/lib/rhpki-*/logs/transactions")
            self.addCopySpec("/var/lib/rhpki-*/logs/system")
        if csversion in (73, 8):
            self.addCopySpec("/etc/dirsrv/slapd-*/dse.ldif")
            self.addCopySpec("/var/log/dirsrv/slapd-*/access")
            self.addCopySpec("/var/log/dirsrv/slapd-*/errors")
        if csversion == 8:
            self.addCopySpec("/etc/pki-*/CS.cfg")
            self.addCopySpec("/var/lib/pki-*/conf/*cfg*")
            self.addCopySpec("/var/log/pki-*/debug")
            self.addCopySpec("/var/log/pki-*/catalina.*")
            self.addCopySpec("/var/log/pki-*/ra-debug.log")
            self.addCopySpec("/var/log/pki-*/transactions")
            self.addCopySpec("/var/log/pki-*/system")
        return
