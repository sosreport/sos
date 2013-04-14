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

class smartcard(Plugin, RedHatPlugin):
    """Smart Card related information
    """

    files = ('/etc/pam_pkcs11/pam_pkcs11.conf',)
    packages = ('pam_pkcs11',)

    def setup(self):
        self.add_copy_specs([
            "/etc/reader.conf",
            "/etc/reader.conf.d/",
            "/etc/pam_pkcs11/"])
        self.add_cmd_output("pkcs11_inspect debug")
        self.add_cmd_output("pklogin_finder debug")
        self.add_cmd_output("ls -nl /usr/lib*/pam_pkcs11/")
