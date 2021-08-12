# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)
import os


class Mysql(Plugin):

    short_desc = 'MySQL and MariaDB RDBMS'

    plugin_name = "mysql"
    profiles = ('services',)
    mysql_cnf = "/etc/my.cnf"

    pw_warn_text = " (password visible in process listings)"

    option_list = [
        PluginOpt('dbuser', default='mysql', val_type=str,
                  desc='username for database dump collection'),
        PluginOpt('dbpass', default='', val_type=str,
                  desc='password for data dump collection' + pw_warn_text),
        PluginOpt('dbdump', default=False, desc='Collect a database dump')
    ]

    def setup(self):
        super(Mysql, self).setup()

        self.add_copy_spec([
            self.mysql_cnf,
            # Required for MariaDB under pacemaker (MariaDB-Galera)
            "/var/log/mysqld.log",
            "/var/log/mysql/mysqld.log",
            "/var/log/mariadb/mariadb.log",
            "/var/lib/mysql/grastate.dat",
            "/var/lib/mysql/gvwstate.dat"
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

        self.add_cmd_output("du -s /var/lib/mysql/*")


class RedHatMysql(Mysql, RedHatPlugin):

    packages = (
        'mysql-server',
        'mysql',
        'mariadb-server',
        'mariadb',
        'openstack-selinux'
    )

    def setup(self):
        super(RedHatMysql, self).setup()
        self.add_copy_spec([
            "/etc/ld.so.conf.d/mysql-*.conf",
            "/etc/ld.so.conf.d/mariadb-*.conf",
            "/etc/my.cnf.d/*",
            "/var/lib/config-data/puppet-generated/mysql/etc/my.cnf.d/*"
        ])


class DebianMysql(Mysql, DebianPlugin, UbuntuPlugin):

    packages = (
        'mysql-server.*',
        'mysql-common',
        'mariadb-server.*',
        'mariadb-common',
        'percona-xtradb-cluster-server-.*',
    )

    def setup(self):
        super(DebianMysql, self).setup()
        self.add_copy_spec([
            "/etc/mysql/",
            "/var/log/mysql/error.log",
            "/var/lib/mysql/*.err",
            "/var/lib/percona-xtradb-cluster/*.err",
            "/var/lib/percona-xtradb-cluster/grastate.dat",
            "/var/lib/percona-xtradb-cluster/gvwstate.dat",
            "/var/lib/percona-xtradb-cluster/innobackup.*.log",
        ])
        self.add_cmd_output("du -s /var/lib/percona-xtradb-cluster/*")


# vim: set et ts=4 sw=4 :
