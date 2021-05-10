# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin
from pipes import quote
from re import match


class Candlepin(Plugin, RedHatPlugin):

    short_desc = 'Candlepin entitlement management'

    plugin_name = 'candlepin'
    packages = ('candlepin',)

    def setup(self):
        # for external DB, search in /etc/candlepin/candlepin.conf for:
        # org.quartz.dataSource.myDS.URL=..
        #
        # and for DB password, search for
        # org.quartz.dataSource.myDS.password=..
        self.dbhost = "localhost"
        self.dbpasswd = ""
        cfg_file = "/etc/candlepin/candlepin.conf"
        try:
            for line in open(cfg_file).read().splitlines():
                # skip empty lines and lines with comments
                if not line or line[0] == '#':
                    continue
                if match(r"^\s*org.quartz.dataSource.myDS.URL=\S+", line):
                    self.dbhost = line.split('=')[1]
                    # separate hostname from value like
                    # jdbc:postgresql://localhost:5432/candlepin
                    self.dbhost = self.dbhost.split('/')[2].split(':')[0]
                if match(r"^\s*org.quartz.dataSource.myDS.password=\S+", line):
                    self.dbpasswd = line.split('=')[1]
        except (IOError, IndexError):
            # fallback when the cfg file is not accessible or parseable
            pass

        self.add_file_tags({
            '/var/log/candlepin/candlepin.log.*': 'candlepin_log',
            '/var/log/candlepin/err.log.*': 'candlepin_error_log',
            '/etc/candlepin/candlepin.conf': 'candlepin_conf'
        })

        # set the password to os.environ when calling psql commands to prevent
        # printing it in sos logs
        # we can't set os.environ directly now: other plugins can overwrite it
        self.env = {"PGPASSWORD": self.dbpasswd}

        # Always collect the full active log of these
        self.add_copy_spec([
            "/var/log/candlepin/error.log",
            "/var/log/candlepin/candlepin.log"
        ], sizelimit=0)

        # Allow limiting on logrotated logs
        self.add_copy_spec([
            "/etc/candlepin/candlepin.conf",
            "/etc/candlepin/broker.xml",
            "/var/log/candlepin/audit*.log*",
            "/var/log/candlepin/candlepin.log[.-]*",
            "/var/log/candlepin/cpdb*.log*",
            "/var/log/candlepin/cpinit*.log*",
            "/var/log/candlepin/error.log[.-]*",
            # Specific to candlepin, ALL catalina logs are relevant. Adding it
            # here rather than the tomcat plugin to ease maintenance and not
            # pollute non-candlepin sosreports that enable the tomcat plugin
            "/var/log/tomcat*/catalina*log*",
            "/var/log/tomcat*/host-manager*log*",
            "/var/log/tomcat*/localhost*log*",
            "/var/log/tomcat*/manager*log*",
        ])

        self.add_cmd_output("du -sh /var/lib/candlepin/*/*")
        # collect tables sizes, ordered
        _cmd = self.build_query_cmd("\
            SELECT schema_name, relname, \
                   pg_size_pretty(table_size) AS size, table_size \
            FROM ( \
              SELECT \
                pg_catalog.pg_namespace.nspname AS schema_name, \
                relname, \
                pg_relation_size(pg_catalog.pg_class.oid) AS table_size \
              FROM pg_catalog.pg_class \
              JOIN pg_catalog.pg_namespace \
                ON relnamespace = pg_catalog.pg_namespace.oid \
            ) t \
            WHERE schema_name NOT LIKE 'pg_%' \
            ORDER BY table_size DESC;")
        self.add_cmd_output(_cmd, suggest_filename='candlepin_db_tables_sizes',
                            env=self.env)

    def build_query_cmd(self, query, csv=False):
        """
        Builds the command needed to invoke the pgsql query as the postgres
        user.
        The query requires significant quoting work to satisfy both the
        shell and postgres parsing requirements. Note that this will generate
        a large amount of quoting in sos logs referencing the command being run
        """
        csvformat = "-A -F , -X" if csv else ""
        _dbcmd = "psql --no-password -h %s -p 5432 -U candlepin \
                  -d candlepin %s -c %s"
        return _dbcmd % (self.dbhost, csvformat, quote(query))

    def postproc(self):
        reg = r"(((.*)(pass|token|secret)(.*))=)(.*)"
        repl = r"\1********"
        self.do_file_sub("/etc/candlepin/candlepin.conf", reg, repl)
        cpdbreg = r"(--password=)([a-zA-Z0-9]*)"
        self.do_file_sub("/var/log/candlepin/cpdb.log", cpdbreg, repl)
        for key in ["trustStorePassword", "keyStorePassword"]:
            self.do_file_sub("/etc/candlepin/broker.xml",
                             r"%s=(\w*)([;<])" % key,
                             r"%s=********\2" % key)

# vim: set et ts=4 sw=4 :
