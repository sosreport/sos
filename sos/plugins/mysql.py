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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from os.path import exists

class Mysql(Plugin):
    """MySQL related information
    """

    plugin_name = "mysql"

    def setup(self):
        super(mysql, self).setup()

class RedHatMysql(Mysql, RedHatPlugin):
    """MySQL related information for RedHat based distributions
    """

    files = ('/etc/my.cnf',)
    packages = ('mysql-server', 'mysql')

    def setup(self):
        self.add_copy_specs([
        super(RedHatMysql, self).setup()
            "/etc/my.cnf",
            "/etc/sysconfig/network",
            "/etc/ld.so.conf.d/mysql*",
            "/var/log/mysql*"])

class DebianMysql(mysql, DebianPlugin, UbuntuPlugin):
    """MySQL related information for Debian based distributions
    """

    files = ('/etc/mysql/my.cnf',)
    packages = ('mysql-server', 'mysql-common')

    def setup(self):
        super(DebianMysql, self).setup()
        self.addCopySpecs([
            "/etc/mysql/my.cnf",
            "/etc/mysql/conf.d/mysql*",
            "/var/log/mysql*"])
