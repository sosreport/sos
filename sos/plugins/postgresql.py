import os
import fnmatch
import shlex
import subprocess
import tempfile

from sos.plugins import Plugin, RedHatPlugin
from sos.utilities import find

class postgresql(Plugin, RedHatPlugin):
    """PostgreSQL related information"""

    packages = ('postgresql',)

    tmp_dir = None

    optionList = [
        ("pghome",  'PostgreSQL server home directory.', '', '/var/lib/pgsql'),
        ("username",  'username for pg_dump', '', 'postgres'),
        ("password",  'password for pg_dump', '', ''),
        ("dbname",  'database name to dump for pg_dump', '', ''),
    ]

    def pg_dump(self):
        dest_file = os.path.join(self.tmp_dir, "sos_pgdump.tar")
        old_env_pgpassword = os.environ.get("PGPASSWORD")
        os.environ["PGPASSWORD"] = self.getOption("password")
        (status, output, rtime) = self.callExtProg("pg_dump %s -U %s -w -f %s -F t" %
                                                   (self.getOption("dbname"),
                                                    self.getOption("username"),
                                                    dest_file))
        if old_env_pgpassword is not None:
            os.environ["PGPASSWORD"] = old_env_pgpassword
        if (status == 0):
            self.addCopySpec(dest_file)
        else:
            self.addAlert("ERROR: Unable to execute pg_dump.  Error(%s)" % (output))

    def setup(self):
        if self.getOption("dbname"):
            if self.getOption("password"):
                self.tmp_dir = tempfile.mkdtemp()
                self.pg_dump()
            else:
                self.addAlert("WARN: password must be supplied to dump a database.")

        # Copy PostgreSQL log files.
        for file in find("*.log", self.getOption("pghome")):
            self.addCopySpec(file)
        # Copy PostgreSQL config files.
        for file in find("*.conf", self.getOption("pghome")):
            self.addCopySpec(file)

        self.addCopySpec(os.path.join(self.getOption("pghome"), "data" , "PG_VERSION"))
        self.addCopySpec(os.path.join(self.getOption("pghome"), "data" , "postmaster.opts"))


    def postproc(self):
        import shutil
        shutil.rmtree(self.tmp_dir)
