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

from sos.plugins import (Plugin, UbuntuPlugin, DebianPlugin, SCLPlugin)
from sos.utilities import find


class PostgreSQL(Plugin):
    """PostgreSQL RDBMS"""

    plugin_name = "postgresql"
    profiles = ('services',)

    packages = ('postgresql', 'postgresql-common')

    password_warn_text = " (password visible in process listings)"

    option_list = [
        ('pghome', 'PostgreSQL server home directory.', '', '/var/lib/pgsql'),
        ('username', 'username for pg_dump', '', 'postgres'),
        ('password', 'password for pg_dump' + password_warn_text, '', False),
        ('dbname', 'database name to dump for pg_dump', '', ''),
        ('dbhost', 'database hostname/IP (do not use unix socket)', '', ''),
        ('dbport', 'database server port number', '', '5432')
    ]

    def do_pg_dump(self, scl=None, filename="pgdump.tar"):
        if self.get_option("dbname"):
            if self.get_option("password") or "PGPASSWORD" in os.environ:
                # We're only modifying this for ourself and our children so
                # there is no need to save and restore environment variables if
                # the user decided to pass the password on the command line.
                if self.get_option("password") is not False:
                    os.environ["PGPASSWORD"] = str(self.get_option("password"))

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
        'rh-postgresql10-postgresql-server'
    )

    def setup(self):
        super(RedHatPostgreSQL, self).setup()

        pghome = self.get_option("pghome")

        scl = None
        for pkg in self.packages[1:]:
            # The scl name, package name, and service name all differ slightly
            # but is at least consistent in doing so across versions, so we
            # need to do some mangling here
            if self.service_is_running(pkg.replace('-server', '')):
                scl = pkg.split('-postgresql-')[0]

        # Copy PostgreSQL log files.
        for filename in find("*.log", pghome):
            self.add_copy_spec(filename)
        for filename in find("*.log", self.convert_copyspec_scl(scl, pghome)):
            self.add_copy_spec(filename)

        # Copy PostgreSQL config files.
        for filename in find("*.conf", pghome):
            self.add_copy_spec(filename)
        for filename in find("*.conf", self.convert_copyspec_scl(scl, pghome)):
            self.add_copy_spec(filename)

        self.add_copy_spec(os.path.join(pghome, "data", "PG_VERSION"))
        self.add_copy_spec(os.path.join(pghome, "data", "postmaster.opts"))

        self.add_copy_spec_scl(scl, os.path.join(pghome, "data", "PG_VERSION"))
        self.add_copy_spec_scl(scl, os.path.join(
                pghome,
                "data",
                "postmaster.opts"
            )
        )

        if scl and scl in self.scls_matched:
            self.do_pg_dump(scl=scl, filename="pgdump-scl-%s.tar" % scl)


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
