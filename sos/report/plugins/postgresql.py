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

from sos.report.plugins import (Plugin, UbuntuPlugin, DebianPlugin, SCLPlugin,
                                PluginOpt)
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

    def do_pg_dump(self, scl=None, filename="pgdump.tar"):
        if self.get_option("dbname"):
            if self.get_option("password") or "PGPASSWORD" in os.environ:
                # We're only modifying this for ourself and our children so
                # there is no need to save and restore environment variables if
                # the user decided to pass the password on the command line.
                if self.get_option("password"):
                    os.environ["PGPASSWORD"] = self.get_option("password")

                if self.get_option("dbhost"):
                    cmd = "pg_dump -U %s -h %s -p %s -w -F t %s" % (
                        self.get_option("username"),
                        self.get_option("dbhost"),
                        self.get_option("dbport"),
                        self.get_option("dbname")
                    )
                else:
                    cmd = "pg_dump -C -U %s -w -F t %s " % (
                        self.get_option("username"),
                        self.get_option("dbname")
                    )

                if scl is not None:
                    cmd = self.convert_cmd_scl(scl, cmd)
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
        self.add_cmd_output("du -sh %s" % self.get_option('pghome'))


class RedHatPostgreSQL(PostgreSQL, SCLPlugin):

    packages = (
        'postgresql',
        'rh-postgresql95-postgresql-server',
        'rh-postgresql10-postgresql-server',
        'rh-postgresql12-postgresql-server',
    )

    def setup(self):
        super(RedHatPostgreSQL, self).setup()

        pghome = self.get_option("pghome")
        dirs = [pghome]

        for pkg in self.packages[1:]:
            # The scl name, package name, and service name all differ slightly
            # but is at least consistent in doing so across versions, so we
            # need to do some mangling here
            scl = pkg.split('-postgresql-')[0]
            _dir = self.convert_copyspec_scl(scl, pghome)
            dirs.append(_dir)
            if self.path_isdir(_dir):
                self.add_cmd_output("du -sh %s" % _dir)
            if (self.is_service_running(pkg.replace('-server', '')) and
                    scl in self.scls_matched):
                self.do_pg_dump(scl=scl, filename="pgdump-scl-%s.tar" % scl)

        for _dir in dirs:
            # Copy PostgreSQL log files.
            for filename in find("*.log", _dir):
                self.add_copy_spec(filename)

            # Copy PostgreSQL config files.
            for filename in find("*.conf", _dir):
                self.add_copy_spec(filename)

            # copy PG_VERSION and postmaster.opts
            for f in ["PG_VERSION", "postmaster.opts"]:
                self.add_copy_spec(self.path_join(_dir, "data", f))


class DebianPostgreSQL(PostgreSQL, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianPostgreSQL, self).setup()

        self.add_copy_spec([
            "/var/log/postgresql/*.log",
            "/etc/postgresql/*/main/*.conf",
            "/var/lib/postgresql/*/main/PG_VERSION",
            "/var/lib/postgresql/*/main/postmaster.opts"
        ])


# vim: set et ts=4 sw=4 :
