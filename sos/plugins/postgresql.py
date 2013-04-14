import os
import tempfile

from sos.plugins import Plugin, RedHatPlugin
from sos.utilities import find

class postgresql(Plugin, RedHatPlugin):
    """PostgreSQL related information"""

    packages = ('postgresql',)

    tmp_dir = None

    option_list = [
        ("pghome",  'PostgreSQL server home directory.', '', '/var/lib/pgsql'),
        ("username",  'username for pg_dump', '', 'postgres'),
        ("password",  'password for pg_dump', '', ''),
        ("dbname",  'database name to dump for pg_dump', '', ''),
    ]

    def pg_dump(self):
        dest_file = os.path.join(self.tmp_dir, "sos_pgdump.tar")
        old_env_pgpassword = os.environ.get("PGPASSWORD")
        os.environ["PGPASSWORD"] = self.get_option("password")
        (status, output, rtime) = self.call_ext_prog("pg_dump %s -U %s -w -f %s -F t" %
                                                   (self.get_option("dbname"),
                                                    self.get_option("username"),
                                                    dest_file))
        if old_env_pgpassword is not None:
            os.environ["PGPASSWORD"] = old_env_pgpassword
        if (status == 0):
            self.add_copy_spec(dest_file)
        else:
            self.add_alert("ERROR: Unable to execute pg_dump.  Error(%s)" % (output))

    def setup(self):
        if self.get_option("dbname"):
            if self.get_option("password"):
                self.tmp_dir = tempfile.mkdtemp()
                self.pg_dump()
            else:
                self.add_alert("WARN: password must be supplied to dump a database.")

        # Copy PostgreSQL log files.
        for file in find("*.log", self.get_option("pghome")):
            self.add_copy_spec(file)
        # Copy PostgreSQL config files.
        for file in find("*.conf", self.get_option("pghome")):
            self.add_copy_spec(file)

        self.add_copy_spec(os.path.join(self.get_option("pghome"), "data" , "PG_VERSION"))
        self.add_copy_spec(os.path.join(self.get_option("pghome"), "data" , "postmaster.opts"))


    def postproc(self):
        import shutil
        if self.tmp_dir:
            shutil.rmtree(self.tmp_dir)
