## Copyright (C) 2010 Red Hat, Inc., Kashyap Chamarthy <kchamart@redhat.com>

## This program is free software; you can redistribute it and/or modify
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
import glob

class dogtag(sos.plugintools.PluginBase):
    """Certificate System diagnostic information
    """
    # This is for dogtag Certificate System

    def checkenabled(self):
       if self.isInstalled("pki-ca") or len(glob.glob("/var/lib/pki-*")):
          return True
       return False

    def setup(self):
        self.addCopySpec("/var/lib/pki-*/logs/*")
        self.addCopySpec("/var/lib/pki-*/conf/*cfg*")
        self.addCopySpec("/var/log/dirsrv/*")
        self.addCopySpec("/var/log/messages")
	return

