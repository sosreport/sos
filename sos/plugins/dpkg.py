## Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>
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

from sos.plugins import Plugin, DebianPlugin, UbuntuPlugin

class dpkg(Plugin, DebianPlugin, UbuntuPlugin):
    """dpkg information
    """
    def setup(self):
        self.addCopySpec("/var/log/dpkg.log")
        self.addCmdOutput("/usr/bin/dpkg -l", root_symlink = "installed-debs")
