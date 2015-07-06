# Copyright (C) 2014 Red Hat, Inc., Sandro Bonazzola <sbonazzo@redhat.com>
# Copyright (C) 2013 Chris J Arges <chris.j.arges@canonical.com>
# Copyright (C) 2012-2013 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
# Copyright (C) 2011 Red Hat, Inc., Jesse Jaggars <jjaggars@redhat.com>

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

import os
import tempfile

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
from sos.utilities import find


class PostgreSQL(Plugin):
    """PostgreSQL RDBMS"""

    plugin_name = "postgresql"
    profiles = ('services',)

    packages = ('postgresql',)

    tmp_dir = None

    password_warn_text = " (password visible in process listings)"

    option_list = [
        ('pghome', 'PostgreSQL server home directory.', '', '/var/lib/pgsql'),
        ('username', 'username for pg_dump', '', 'postgres'),
        ('password', 'password for pg_dump' + password_warn_text, '', False),
        ('dbname', 'database name to dump for pg_dump', '', ''),
        ('dbhost', 'database hostname/IP (do not use unix socket)', '', ''),
        ('dbport', 'database server port number', '', '5432')
    ]

    def pg_dump(self):
        dest_file = os.path.join(self.tmp_dir, "sos_pgdump.tar")
        # We're only modifying this for ourself and our children so there
        # is no need to save and restore environment variables if the user
        # decided to pass the password on the command line.
        if self.get_option("password") is not False:
            os.environ["PGPASSWORD"] = str(self.get_option("password"))

        if self.get_option("dbhost"):
            cmd = "pg_dump -U %s -h %s -p %s -w -f %s -F t %s" % (
                self.get_option("username"),
                self.get_option("dbhost"),
                self.get_option("dbport"),
                dest_file,
                self.get_option("dbname")
            )
        else:
            cmd = "pg_dump -C -U %s -w -f %s -F t %s " % (
                self.get_option("username"),
                dest_file,
                self.get_option("dbname")
            )

        result = self.call_ext_prog(cmd)
        if (result['status'] == 0):
            self.add_copy_spec(dest_file)
        else:
            self._log_error(
                "Unable to execute pg_dump. Error(%s)" % (result['output'])
            )
            self.add_alert(
                "ERROR: Unable to execute pg_dump. Error(%s)" %
                (result['output'])
            )

    def setup(self):
        if self.get_option("dbname"):
            if self.get_option("password") or "PGPASSWORD" in os.environ:
                self.tmp_dir = tempfile.mkdtemp()
                self.pg_dump()
            else:
                self.soslog.warning(
                    "password must be supplied to dump a database."
                )
                self.add_alert(
                    "WARN: password must be supplied to dump a database."
                )

    def postproc(self):
        import shutil
        if self.tmp_dir:
            try:
                shutil.rmtree(self.tmp_dir)
            except shutil.Error:
                self.soslog.exception(
                    "Unable to remove %s." % (self.tmp_dir)
                )
                self.add_alert("ERROR: Unable to remove %s." % (self.tmp_dir))


class RedHatPostgreSQL(PostgreSQL, RedHatPlugin):

    def setup(self):
        super(RedHatPostgreSQL, self).setup()

        # Copy PostgreSQL log files.
        for filename in find("*.log", self.get_option("pghome")):
            self.add_copy_spec(filename)
        # Copy PostgreSQL config files.
        for filename in find("*.conf", self.get_option("pghome")):
            self.add_copy_spec(filename)

        self.add_copy_spec(
            os.path.join(
                self.get_option("pghome"),
                "data",
                "PG_VERSION"
            )
        )
        self.add_copy_spec(
            os.path.join(
                self.get_option("pghome"),
                "data",
                "postmaster.opts"
            )
        )


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
