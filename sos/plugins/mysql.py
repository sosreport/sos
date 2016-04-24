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
import os


class Mysql(Plugin):
    """MySQL and MariaDB RDBMS
    """

    plugin_name = "mysql"
    profiles = ('services',)
    mysql_cnf = "/etc/my.cnf"

    pw_warn_text = " (password visible in process listings)"

    option_list = [
        ("dbuser", "username for database dumps", "", "mysql"),
        ("dbpass", "password for database dumps" + pw_warn_text, "", False),
        ("dbdump", "collect a database dump", "", False)
    ]

    def setup(self):
        super(Mysql, self).setup()

        self.add_copy_spec([
            self.mysql_cnf,
            # Required for MariaDB under pacemaker (MariaDB-Galera)
            "/var/log/mysqld.log",
            "/var/log/mysql/mysqld.log",
            "/var/log/mariadb/mariadb.log",
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/mysql*",
                "/var/log/mariadb*"
            ])

        if self.get_option("dbdump"):
            msg = "database user name and password must be supplied"
            dbdump_err = "mysql.dbdump: %s" % msg

            dbuser = self.get_option("dbuser")
            dbpass = self.get_option("dbpass")

            if 'MYSQL_PWD' in os.environ:
                dbpass = os.environ['MYSQL_PWD']

            if dbuser is True or dbpass is True:
                # sosreport -a or -k mysql.{dbuser,dbpass}
                self.soslog.warning(dbdump_err)
                return

            if not dbpass or dbpass is False:
                # no MySQL password
                self.soslog.warning(dbdump_err)
                return

            # no need to save/restore as this variable is private to
            # the mysql plugin.
            os.environ['MYSQL_PWD'] = dbpass

            opts = "--user=%s --all-databases" % dbuser
            name = "mysqldump_--all-databases"
            self.add_cmd_output("mysqldump %s" % opts, suggest_filename=name)


class RedHatMysql(Mysql, RedHatPlugin):

    packages = (
        'mysql-server',
        'mysql',
        'mariadb-server',
        'mariadb'
    )

    def setup(self):
        super(RedHatMysql, self).setup()
        self.add_copy_spec([
            "/etc/ld.so.conf.d/mysql-*.conf",
            "/etc/ld.so.conf.d/mariadb-*.conf"
        ])
        self.add_copy_spec("/etc/my.cnf.d/*")


class DebianMysql(Mysql, DebianPlugin, UbuntuPlugin):

    packages = (
        'mysql-server',
        'mysql-common',
        'mariadb-server',
        'mariadb-common'
    )

    def setup(self):
        super(DebianMysql, self).setup()
        self.add_copy_spec("/etc/mysql/conf.d/mysql*")

# vim: set et ts=4 sw=4 :
