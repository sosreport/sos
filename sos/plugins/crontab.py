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

class crontab(sos.plugintools.PluginBase):
    """Crontab information
    """
    def setup(self):
        self.addCopySpec("/etc/cron*")
        self.collectExtOutput("/usr/bin/crontab -l -u root", suggest_filename = "root_crontab")
        self.collectExtOutput("""for i in `ls /home/`;\
        do echo "User :" $i;/usr/bin/crontab -l -u $i;\
        echo "---------------";done""", suggest_filename = "users_crontabs")
        return
