import fnmatch
import os
import sos.plugintools
import tempfile

def find(file_pattern, top_dir, max_depth=None, path_pattern=None):
    """generate function to find files recursively. Usage:

     for filename in find("*.properties", /var/log/foobar):
         print filename
    """
    if max_depth:
        base_depth = os.path.dirname(top_dir).count(os.path.sep)
        max_depth += base_depth

    for path, dirlist, filelist in os.walk(top_dir):
        if max_depth and path.count(os.path.sep) >= max_depth:
            del dirlist[:]

        if path_pattern and not fnmatch.fnmatch(path, path_pattern):
            continue

        for name in fnmatch.filter(filelist, file_pattern):
            yield os.path.join(path,name)

# Class name must be the same as file name and method names must not change
class psql(sos.plugintools.PluginBase):
    """PostgreSQL related information"""
    __pghome = '/var/lib/pgsql'
    __username = 'postgres'
    __dbport = 5432

    packages = [ 'postgresql' ]

    tmp_dir = None

    optionList = [
        ("pghome",  'PostgreSQL server home directory (default=/var/lib/pgsql)', '', False),
        ("username",  'username for pg_dump (default=postgres)', '', False),
        ("password",  'password for pg_dump (default=None)', '', False),
        ("dbname",  'database name to dump for pg_dump (default=None)', '', False),
        ("dbhost",  'hostname/IP of the server upon which the DB is running (default=localhost)', '', False),
        ("dbport",  'database server port number (default=5432)', '', False)
    ]

    def pg_dump(self):
        dest_file = os.path.join(self.tmp_dir, "sos_pgdump.tar")
        old_env_pgpassword = os.environ.get("PGPASSWORD")
        os.environ["PGPASSWORD"] = "%s" % (self.getOption("password"))
        if self.getOption("dbhost"):
            (status, output, rtime) = self.callExtProg("pg_dump -U %s -h %s -p %s -w -f %s -F t %s" %
                                           (self.__username,
                                            self.getOption("dbhost"),
                                            self.__dbport,
                                            dest_file,
                                            self.getOption("dbname")))
        else:
            (status, output, rtime) = self.callExtProg("pg_dump -C -U %s -w -f %s -F t %s " %
                                                       (self.__username,
                                                        dest_file,
                                                        self.getOption("dbname")))

        if old_env_pgpassword is not None:
            os.environ["PGPASSWORD"] = str(old_env_pgpassword)
        if (status == 0):
            self.addCopySpec(dest_file)
        else:
            self.addAlert("ERROR: Unable to execute pg_dump.  Error(%s)" % (output))

    def setup(self):
        if self.getOption("pghome"):
            self.__pghome = self.getOption("pghome")

        if self.getOption("dbname"):
            if self.getOption("password"):
                if self.getOption("username"):
                    self.__username = self.getOption("username")
                if self.getOption("dbport"):
                    self.__dbport = self.getOption("dbport")
                self.tmp_dir = tempfile.mkdtemp()
                self.pg_dump()
            else:
                self.addAlert("WARN: password must be supplied to dump a database.")

        # Copy PostgreSQL log files.
        for file in find("*.log", self.__pghome):
            self.addCopySpec(file)
        # Copy PostgreSQL config files.
        for file in find("*.conf", self.__pghome):
            self.addCopySpec(file)

        self.addCopySpec(os.path.join(self.__pghome, "data" , "PG_VERSION"))
        self.addCopySpec(os.path.join(self.__pghome, "data" , "postmaster.opts"))


    def postproc(self):
        import shutil
        if self.tmp_dir == None:
            return
        try:
            shutil.rmtree(self.tmp_dir)
        except:
            self.addAlert("ERROR: Unable to remove %s." % (self.tmp_dir))
