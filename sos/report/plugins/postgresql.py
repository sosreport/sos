# Copyright (C) 2017 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>
# Copyright (C) 2014 Red Hat, Inc., Sandro Bonazzola <sbonazzo@redhat.com>
# Copyright (C) 2013 Chris J Arges <chris.j.arges@canonical.com>
# Copyright (C) 2012-2013 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
# Copyright (C) 2011 Red Hat, Inc., Jesse Jaggars <jjaggars@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from sos.report.plugins import (Plugin, UbuntuPlugin, DebianPlugin,
                                RedHatPlugin, PluginOpt)
from sos.utilities import find


class PostgreSQL(Plugin):

    short_desc = 'PostgreSQL RDBMS'

    plugin_name = "postgresql"
    profiles = ('services',)

    packages = ('postgresql', 'postgresql-common')

    password_warn_text = " (password visible in process listings)"

    option_list = [
        PluginOpt('pghome', default='/var/lib/pgsql',
                  desc='psql server home directory'),
        PluginOpt('username', default='postgres', val_type=str,
                  desc='username for pg_dump'),
        PluginOpt('password', default='', val_type=str,
                  desc='password for pg_dump' + password_warn_text),
        PluginOpt('dbname', default='', val_type=str,
                  desc='database name to dump with pg_dump'),
        PluginOpt('dbhost', default='', val_type=str,
                  desc='database hostname/IP address (no unix sockets)'),
        PluginOpt('dbport', default=5432, val_type=int,
                  desc='database server listening port')
    ]

    def do_pg_dump(self, filename="pgdump.tar"):
        """ Extract PostgreSQL database into a tar file """
        if self.get_option("dbname"):
            if self.get_option("password") or "PGPASSWORD" in os.environ:
                # We're only modifying this for ourself and our children so
                # there is no need to save and restore environment variables if
                # the user decided to pass the password on the command line.
                if self.get_option("password"):
                    os.environ["PGPASSWORD"] = self.get_option("password")

                if self.get_option("dbhost"):
                    cmd = (f"pg_dump -U {self.get_option('username')} "
                           f"-h {self.get_option('dbhost')} "
                           f"-p {self.get_option('dbport')} -w -F t "
                           f"{self.get_option('dbname')}")
                else:
                    cmd = (f"pg_dump -C -U {self.get_option('username')} -w "
                           f"-F t {self.get_option('dbname')}")

                self.add_cmd_output(cmd, suggest_filename=filename,
                                    binary=True, sizelimit=0)

            else:  # no password in env or options
                self.soslog.warning(
                    "password must be supplied to dump a database."
                )
                self.add_alert(
                    "WARN: password must be supplied to dump a database."
                )

    def setup(self):
        self.do_pg_dump()
        self.add_cmd_output(f"du -sh {self.get_option('pghome')}")


class RedHatPostgreSQL(PostgreSQL, RedHatPlugin):

    def setup(self):
        super().setup()

        pghome = self.get_option("pghome")
        dirs = [pghome]

        for _dir in dirs:
            # Copy PostgreSQL log files.
            for filename in find("*.log", _dir):
                self.add_copy_spec(filename)

            # Copy PostgreSQL config files.
            for filename in find("*.conf", _dir):
                self.add_copy_spec(filename)

            # copy PG_VERSION and postmaster.opts
            for file in ["PG_VERSION", "postmaster.opts"]:
                self.add_copy_spec(self.path_join(_dir, "data", file))


class DebianPostgreSQL(PostgreSQL, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super().setup()

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/postgresql/")
        else:
            self.add_copy_spec("/var/log/postgresql/*.log")

        self.add_copy_spec([
            "/etc/postgresql/*/main/*.conf",
            "/var/lib/postgresql/*/main/PG_VERSION",
            "/var/lib/postgresql/*/main/postmaster.opts"
        ])


# vim: set et ts=4 sw=4 :
