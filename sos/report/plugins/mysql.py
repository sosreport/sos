# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)


class Mysql(Plugin):

    short_desc = 'MySQL and MariaDB RDBMS'

    plugin_name = "mysql"
    profiles = ('services',)
    mysql_cnf = "/etc/my.cnf"
    my_cnf_dir = "/etc/my.cnf.d"

    pw_warn_text = " (password visible in process listings)"

    option_list = [
        PluginOpt('dbuser', default='mysql', val_type=str,
                  desc='username for database dump collection'),
        PluginOpt('dbpass', default='', val_type=str,
                  desc='password for data dump collection' + pw_warn_text),
        PluginOpt('dbdump', default=False, desc='Collect a database dump')
    ]

    def setup(self):
        super().setup()

        self.add_copy_spec([
            self.mysql_cnf,
            "/etc/mysqlrouter/",
            "/var/lib/mysql/grastate.dat",
            "/var/lib/mysql/gvwstate.dat"
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/mysql*",
                "/var/log/mariadb*",
                "/var/log/mysqlrouter/*"
            ])
        else:
            self.add_copy_spec([
                # Required for MariaDB under pacemaker (MariaDB-Galera)
                "/var/log/mysqld.log",
                "/var/log/mysql/mysqld.log",
                "/var/log/mysqlrouter/mysqlrouter.log",
                "/var/log/mariadb/mariadb.log"
            ])

        if self.get_option("dbdump"):
            msg = "database user name and password must be supplied"
            dbdump_err = f"mysql.dbdump: {msg}"

            dbuser = self.get_option("dbuser")
            dbpass = self.get_option("dbpass")

            if 'MYSQL_PWD' in os.environ:
                dbpass = os.environ['MYSQL_PWD']

            if dbuser is True or dbpass is True:
                # sos report -a or -k mysql.{dbuser,dbpass}
                self.soslog.warning(dbdump_err)
                return

            if not dbpass or dbpass is False:
                # no MySQL password
                self.soslog.warning(dbdump_err)
                return

            # no need to save/restore as this variable is private to
            # the mysql plugin.
            os.environ['MYSQL_PWD'] = dbpass

            opts = f"--user={dbuser} --all-databases"
            name = "mysqldump_--all-databases"
            self.add_cmd_output(f"mysqldump {opts}", suggest_filename=name)

        self.add_cmd_output("du -s /var/lib/mysql/*")

    def postproc(self):
        protect_keys = ['password']
        regex = fr"(^\s*({'|'.join(protect_keys)})\s*=\s*)(.*)"
        sub = r"\1*********"

        self.do_path_regex_sub(
            f"{self.my_cnf_dir}/*",
            regex, sub
        )
        self.do_file_sub(
            f"{self.mysql_cnf}",
            regex, sub
        )


class RedHatMysql(Mysql, RedHatPlugin):

    packages = (
        'mysql-server',
        'mysql',
        'mariadb-server',
        'mariadb',
        'openstack-selinux'
    )

    def setup(self):
        super().setup()
        self.add_copy_spec([
            "/etc/ld.so.conf.d/mysql-*.conf",
            "/etc/ld.so.conf.d/mariadb-*.conf",
            f"{self.my_cnf_dir}/*",
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

    my_cnf_dir = "/etc/mysql/"
    mysql_cnf = f"{my_cnf_dir}/my.cnf"

    def setup(self):
        super().setup()
        self.add_copy_spec([
            self.my_cnf_dir,
            "/var/log/mysql/error.log",
            "/var/lib/mysql/*.err",
            "/var/lib/percona-xtradb-cluster/*.err",
            "/var/lib/percona-xtradb-cluster/grastate.dat",
            "/var/lib/percona-xtradb-cluster/gvwstate.dat",
            "/var/lib/percona-xtradb-cluster/innobackup.*.log",
        ])
        self.add_cmd_output("du -s /var/lib/percona-xtradb-cluster/*")


# vim: set et ts=4 sw=4 :
