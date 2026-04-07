# Copyright (C) 2021 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
import sqlite3

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt, UbuntuPlugin


class OpenStackDatabase(Plugin):

    short_desc = 'Openstack Database Information'
    plugin_name = 'openstack_database'
    profiles = ('openstack', 'openstack_controller')

    option_list = [
        PluginOpt('dump', default=False, desc='Dump select databases'),
        PluginOpt('dumpall', default=False, desc='Dump ALL databases'),
        PluginOpt("dbpass", default="", val_type=str,
                  desc="Password for database dump collection"),
    ]

    databases = [
        'cinder',
        'glance',
        'heat',
        'ironic',
        'keystone',
        'mistral',
        '(.*)?neutron',
        'nova.*'
    ]

    def setup(self):
        # determine if we're running databases on the host or in a container
        _db_containers = [
            'galera-bundle-.*',  # overcloud
            'mysql'  # undercloud
        ]

        cname = None
        for container in _db_containers:
            cname = self.get_container_by_name(container)
            if cname:
                break

        fname = f"clustercheck_{cname}" if cname else None
        self.add_cmd_output('clustercheck', container=cname, timeout=15,
                            suggest_filename=fname)

        if self.get_option('dump') or self.get_option('dumpall'):
            db_dump = self.get_mysql_db_string(container=cname)
            dbpass = self.get_mysql_password()
            db_cmd = f"mysqldump --opt {db_dump}"

            # Pass password via MYSQL_PWD env var if available
            mysql_env = {"MYSQL_PWD": dbpass} if dbpass else None

            self.add_cmd_output(db_cmd, suggest_filename='mysql_dump.sql',
                                sizelimit=0, container=cname, env=mysql_env)

    def get_mysql_password(self):
        """Return MySQL password from user-provided option (default: empty)."""
        return self.get_option("dbpass") or ""

    def get_mysql_db_string(self, container=None):
        """ Get mysql DB command to be dumped """
        if self.get_option('dumpall'):
            return '--all-databases'

        collect = []
        dbs = self.exec_cmd('mysql -e "show databases;"', container=container)

        for database in dbs['output'].splitlines():
            if any(re.match(database, reg) for reg in self.databases):
                collect.append(database)

        return '-B ' + ' '.join(d for d in collect)


class RedHatOpenStackDatabase(OpenStackDatabase, RedHatPlugin):

    packages = ('openstack-selinux', )


class UbuntuOpenStackDatabase(OpenStackDatabase, UbuntuPlugin):

    packages = ('mysql-server',)

    def get_mysql_password(self):
        """
        Return MySQL password.
        1. User provided option (--dbpass)
        2. SQLite (Ubuntu only)
        3. Default empty (no password)
        """

        # 1. Try user provided password
        dbpass = self.get_option("dbpass")
        if dbpass:
            return dbpass

        # 2. Try SQLite
        sqlite_file = self.find_mysql_sqlite_file()
        if sqlite_file:
            try:
                conn = sqlite3.connect(sqlite_file)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data FROM kv "
                    "WHERE key='leadership.settings.mysql.passwd';"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]  # password from SQLite
            except Exception:
                # If SQLite read fails continue to default
                pass
            finally:
                if 'conn' in locals():
                    conn.close()

        # 3. Fallback to default: no password
        return ""

    def find_mysql_sqlite_file(self):
        """
        Dynamically locate the Juju SQLite file for MySQL password.
        Returns the full path if found, else None.
        """
        base_path = "/var/lib/juju/agents/"
        try:
            for unit_dir in self.listdir(base_path):
                charm_path = f"{base_path}/{unit_dir}/charm"
                meta_file = f"{charm_path}/metadata.yaml"
                if self.path_exists(meta_file):
                    sqlite_file = f"{charm_path}/.unit-state.db"
                    if self.path_exists(sqlite_file):
                        return sqlite_file
        except Exception:
            pass
        return None


# vim: set et ts=4 sw=4 :
