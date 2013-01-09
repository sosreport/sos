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
class pgsql(sos.plugintools.PluginBase):
    """PostgreSQL related information"""
    __pghome = '/var/lib/pgsql'
    __username = 'postgres'
    __dbport = 5432

    packages = [ 'postgresql' ]

    optionList = [
        ("pghome",  'PostgreSQL server home directory (default=/var/lib/pgsql)', '', __pghome),
        ("username",  'username for pg_dump (default=postgres)', '', False),
        ("password",  'password for pg_dump (default=None)', '', False),
        ("dbname",  'database name to dump for pg_dump (default=None)', '', False),
        ("dbhost",  'hostname/IP of the server upon which the DB is running (default=localhost)', '', False),
        ("dbport",  'database server port number (default=5432)', '', False)
    ]

    def pg_dump(self):
        dest_dir = os.path.join(self.cInfo['cmddir'], "pgsql")
        dest_file = os.path.join(dest_dir, "sos_pgdump.tar")
        try:
            os.makedirs(dest_dir)
        except:
            self.soslog.error("could not create pg_dump output path %s" % dest_dir)
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
        if status != 0:
            self.soslog.error("unable to execute pg_dump.  Error(%s)" % (output))

    def setup(self):
        if self.getOption("pghome"):
            self.__pghome = str(self.getOption("pghome")).strip()

        if os.path.isdir(self.__pghome):            
            # Copy PostgreSQL log files.
            for file in find("*.log", self.__pghome):
                self.addCopySpec(file)
            # Copy PostgreSQL config files.
            for file in find("*.conf", self.__pghome):
                self.addCopySpec(file)
            self.addCopySpec(os.path.join(self.__pghome,
                            "data" , "PG_VERSION"))
            self.addCopySpec(os.path.join(self.__pghome,
                            "data" , "postmaster.opts"))

        if self.getOption("dbname"):
            if self.getOption("dbname") == True:
                # dbname must have a value
                self.soslog.warn("pgsql.dbname requires a database name")
                return
            if self.getOption("password") != False:
                if self.getOption("username"):
                    if self.getOption("username") == True:
                        self.soslog.warn("pgsql.username requires a user name")
                        return
                    self.__username = self.getOption("username")
                if self.getOption("dbport"):
                    if self.getOption("dbport") == True:
                        self.soslog.warn("pgsql.dbport requires a port value")
                        return
                    self.__dbport = self.getOption("dbport")
                self.pg_dump()
            else:
                self.soslog.warn("password must be supplied to dump a database.")

