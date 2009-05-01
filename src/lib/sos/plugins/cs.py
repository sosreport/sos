## Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>

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

#############################################################
# This plugin assumes default location of Certificate System 7.x on RHEL4
# Certificate System 7.x is not supported on RHEL5.
# Any improvemts for this plugin are appreciated.  Please send them to
# klamb@redhat.com
# thanks,
# kent lamb
#############################################################


import sos.plugintools
import os

class cs(sos.plugintools.PluginBase):
    """Certificate System 7.x Diagnostic Information
    """
    # check for default location of pki services (/var/lib.rhpki-*).  
    # If default path exists, assume rhpki- glob and grap all installed 
    # subsystems.  If customer has a custom install path, then ln -s the 
    # custom path to /var/lib/rhkpi-installed_subsystem (/var/lib/rhpki-ca, 
    # /var/lib/rhpki-kra ect).

    def checkenabled(self):
       if self.isInstalled("rhpki-common") or os.path.exists("/var/lib/rhpki-*"):
          return True
       return False

    def setup(self):
        self.addCopySpec("/var/lib/rhpki-*/conf/*cfg*")
        self.addCopySpec("/var/lib/rhpki-*/conf/*.ldif")
        self.addCopySpec("/var/lib/rhpki-*/logs/*")
        return


