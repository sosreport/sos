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
from os import listdir
from os.path import exists

class sar(sos.plugintools.PluginBase):
    """Generate the sar file from /var/log/sa/saXX files
    """
    def setup(self):
        path="/var/log/sa"
        dirList=listdir(path)
        # find all the sa file that don't have an existing sar file
        for fname in dirList:
            if fname[0:2] == 'sa' and fname[2] != 'r':
                sar_filename = 'sar' + fname[2:4]
                if sar_filename not in dirList:
                    sar_command = "/bin/sh -c \"LANG=C /usr/bin/sar -A -f /var/log/sa/" + fname + "\""
                    self.collectOutputNow(sar_command, sar_filename, root_symlink=sar_filename)
        return

    def checkenabled(self):
        return exists("/var/log/sa") and os.path.exists("/usr/bin/sar")
