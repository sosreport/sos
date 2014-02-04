import os
import tempfile

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
from sos.utilities import find


class PostgreSQL(Plugin):
    """PostgreSQL related information"""

    plugin_name = "postgresql"

    packages = ('postgresql',)

    tmp_dir = None

    option_list = [
        ('pghome', 'PostgreSQL server home directory.', '', '/var/lib/pgsql'),
        ('username', 'username for pg_dump', '', 'postgres'),
        ('password', 'password for pg_dump', '', ''),
        ('dbname', 'database name to dump for pg_dump', '', ''),
    ]

    def pg_dump(self):
        dest_file = os.path.join(self.tmp_dir, "sos_pgdump.tar")
        old_env_pgpassword = os.environ.get("PGPASSWORD")
        os.environ["PGPASSWORD"] = self.get_option("password")
        (status, output, rtime) = self.call_ext_prog(
            "pg_dump %s -U %s -w -f %s -F t" % (
                self.get_option("dbname"),
                self.get_option("username"),
                dest_file
            )
        )
        if old_env_pgpassword is not None:
            os.environ["PGPASSWORD"] = old_env_pgpassword
        if (status == 0):
            self.add_copy_spec(dest_file)
        else:
            self.add_alert(
                "ERROR: Unable to execute pg_dump.  Error(%s)" % (output)
            )

    def setup(self):
        if self.get_option("dbname"):
            if self.get_option("password"):
                self.tmp_dir = tempfile.mkdtemp()
                self.pg_dump()
            else:
                self.add_alert(
                    "WARN: password must be supplied to dump a database."
                )

    def postproc(self):
        import shutil
        if self.tmp_dir:
            shutil.rmtree(self.tmp_dir)


class RedHatPostgreSQL(PostgreSQL, RedHatPlugin):
    """PostgreSQL related information for Red Hat distributions"""

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
    """PostgreSQL related information for Debian/Ubuntu distributions"""

    def setup(self):
        super(DebianPostgreSQL, self).setup()

        # Copy PostgreSQL log files.
        self.add_copy_spec("/var/log/postgresql/*.log")
        # Copy PostgreSQL config files.
        self.add_copy_spec("/etc/postgresql/*/main/*.conf")

        self.add_copy_spec("/var/lib/postgresql/*/main/PG_VERSION")
        self.add_copy_spec("/var/lib/postgresql/*/main/postmaster.opts")

# vim: expandtab tabstop=4 shiftwidth=4
