# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Mysql(Plugin):
    """MySQL and MariaDB related information
    """

    plugin_name = "mysql"
    mysql_cnf = "/etc/my.cnf"

    option_list = [
        ("dbuser", "username for database dumps", "", "mysql"),
        ("dbpass", "password for database dumps", "", ""),
        ("dbdump", "collect a database dump", "", False)
    ]

    def setup(self):
        super(Mysql, self).setup()
        self.add_copy_specs([
            self.mysql_cnf,
            "/var/log/mysql/mysqld.log",
            "/var/log/mariadb/mariadb.log",
        ])
        if self.get_option("all_logs"):
            self.add_copy_specs([
                "/var/log/mysql*",
                "/var/log/mariadb*"
            ])
        if self.get_option("dbdump"):
            dbuser = self.get_option("dbuser")
            dbpass = self.get_option("dbpass")
            opts = "--user=%s --password=%s --all-databases" % (dbuser, dbpass)
            name = "mysqldump_--all-databases"
            self.add_cmd_output("mysqldump %s" % opts, suggest_filename=name)


class RedHatMysql(Mysql, RedHatPlugin):
    """MySQL and MariaDB information for Red Hat based distributions
    """

    packages = (
        'mysql-server',
        'mysql',
        'mariadb-server',
        'mariadb'
    )

    def setup(self):
        super(RedHatMysql, self).setup()
        self.add_copy_specs([
            "/etc/ld.so.conf.d/mysql-*.conf",
            "/etc/ld.so.conf.d/mariadb-*.conf"
        ])
        self.add_copy_spec("/etc/my.cnf.d/*")


class DebianMysql(Mysql, DebianPlugin, UbuntuPlugin):
    """MySQL and MariaDB information for Debian based distributions
    """

    packages = (
        'mysql-server',
        'mysql-common',
        'mariadb-server',
        'mariadb-common'
    )

    def setup(self):
        super(DebianMysql, self).setup()
        self.add_copy_spec("/etc/mysql/conf.d/mysql*")

# vim: et ts=4 sw=4
