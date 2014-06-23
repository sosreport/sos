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

class mysql(sos.plugintools.PluginBase):
    """MySQL related information
    """
    files = ('/etc/my.cnf',)
    packages = ('mysql-server',)

    optionList = [
        ("dbuser", "username for database dumps", "", "mysql"),
        ("dbpass", "password for database dumps", "", ""),
        ("dbdump", "collect a database dump", "", False),
        ("all_logs", "collect all MySQL logs", "", False)
    ]
        
    def setup(self):
        self.addCopySpec("/etc/my.cnf")
        self.addCopySpec("/etc/ld.so.conf.d/mysql*")

        if not self.getOption("all_logs"):
            self.addCopySpecLimit("/var/log/mysqld.log", 15)
        else:
            self.addCopySpec("/var/log/mysql*")

        if self.getOption("dbdump"):
            dbuser = self.getOption("dbuser")
            dbpass = self.getOption("dbpass")
            opts = "--user=%s --password=%s --all-databases" % (dbuser, dbpass)
            name = "mysqldump_--all-databases"
            self.collectExtOutput("mysqldump %s" % opts, suggest_filename=name)
        return

