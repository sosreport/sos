## Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

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
import os
from time import time

class smartcard(Plugin, RedHatPlugin):
    """Smart Card related information
    """

    def checkenabled(self):
        return self.isInstalled("pam_pkcs11") or os.path.exists("/etc/pam_pkcs11/pam_pkcs11.conf")

    def setup(self):
        self.addCopySpecs([
            "/etc/reader.conf",
            "/etc/reader.conf.d/",
            "/etc/pam_pkcs11/"])
        self.collectExtOutput("/usr/bin/pkcs11_inspect debug")
        self.collectExtOutput("/usr/bin/pklogin_finder debug")
        self.collectExtOutput("/bin/ls -nl /usr/lib*/pam_pkcs11/")
