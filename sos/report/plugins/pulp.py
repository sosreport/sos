# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt
from pipes import quote
from re import match


class Pulp(Plugin, RedHatPlugin):

    short_desc = 'Pulp platform'

    plugin_name = "pulp"
    packages = ("pulp-server", "pulp-katello", "python3-pulpcore")
    files = ("/etc/pulp/settings.py",)
    option_list = [
        PluginOpt('tasks', default=200,
                  desc='number of tasks to collect from DB queries')
    ]

    def setup(self):

        # get mongo DB host and port from line like:
        # seeds: host1:27017,host2:27017
        # take just the very first URI and ignore possible failover
        # if no such config is present, default to localhost:27017
        # further, take optional user credentials - here we assume the
        # credentials dont contain a whitespace character (that would
        # make the parsing more difficult)
        #
        # further, collect location of CA file for contacting qpid in section
        # [messaging]
        # certfile: /etc/pki/katello/qpid_client_striped.crt
        self.dbhost = "localhost"
        self.dbport = "27017"
        self.dbuser = ""
        self.dbpassword = ""
        self.messaging_cert_file = ""
        in_messaging_section = False
        try:
            for line in open("/etc/pulp/server.conf").read().splitlines():
                if match(r"^\s*seeds:\s+\S+:\S+", line):
                    uri = line.split()[1].split(',')[0].split(':')
                    self.dbhost = uri[0]
                    self.dbport = uri[1]
                if match(r"\s*username:\s+\S+", line):
                    self.dbuser = "-u %s" % line.split()[1]
                if match(r"\s*password:\s+\S+", line):
                    self.dbpassword = "-p %s" % line.split()[1]
                if line.startswith("[messaging]"):
                    in_messaging_section = True
                if in_messaging_section and line.startswith("certfile:"):
                    self.messaging_cert_file = line.split()[1]
                    in_messaging_section = False
        except IOError:
            # fallback when the cfg file is not accessible
            pass

        self.add_file_tags({
            '/etc/default/pulp_workers': 'pulp_worker_defaults'
        })

        self.add_copy_spec([
            "/etc/pulp/*.conf",
            "/etc/pulp/settings.py",
            "/etc/pulp/server/plugins.conf.d/",
            "/etc/default/pulp*",
            "/var/log/httpd/pulp-http.log*",
            "/var/log/httpd/pulp-https.log*",
            "/var/log/httpd/pulp-http_access_ssl.log*",
            "/var/log/httpd/pulp-https_access_ssl.log*",
            "/var/log/httpd/pulp-http_error_ssl.log*",
            "/var/log/httpd/pulp-https_error_ssl.log*"
        ])

        num_tasks = self.get_option('tasks')

        mtasks = self.build_mongo_cmd(
            '\"DBQuery.shellBatchSize=%s;; '
            'db.task_status.find().sort({finish_time: -1})'
            '.pretty().shellPrint()\"' % num_tasks
        )

        mres = self.build_mongo_cmd(
            '\"DBQuery.shellBatchSize=%s;; '
            'db.reserved_resources.find().pretty().shellPrint()\"' % num_tasks
        )

        prun = self.build_mongo_cmd(
            r'"DBQuery.shellBatchSize=%s;; '
            r'db.task_status.find({state:{\$ne: \"finished\"}}).pretty()'
            r'.shellPrint()"' % num_tasks
        )

        # prints mongo collection sizes sorted from biggest and in human
        # readable output
        csizes = self.build_mongo_cmd(
            '\"function humanReadable(bytes) {'
            '  var i = -1;'
            '  var byteUnits = [\'kB\', \'MB\', \'GB\', \'TB\', \'PB\', '
            '                   \'EB\', \'ZB\', \'YB\'];'
            '  do {'
            '      bytes = bytes / 1024;'
            '      i++;'
            '  } while (bytes > 1024);'
            '  return Math.max(bytes, 0.1).toFixed(1) + \' \' + byteUnits[i];'
            '};'
            'var collectionNames = db.getCollectionNames(), stats = [];'
            'collectionNames.forEach(function (n) {'
            '                          stats.push(db[n].stats());'
            '                        });'
            'stats = stats.sort(function(a, b) {'
            '                     return b[\'size\'] - a[\'size\']; });'
            'for (var c in stats) {'
            '  print(stats[c][\'ns\'] + \': \' +'
            '        humanReadable(stats[c][\'size\']) + \' (\' +'
            '        humanReadable(stats[c][\'storageSize\']) + \')\'); }\"'
        )

        dbstats = self.build_mongo_cmd('\"db.stats()\"')

        self.add_cmd_output(mtasks, suggest_filename="mongo-task_status")
        self.add_cmd_output(mres, suggest_filename="mongo-reserved_resources")
        self.add_cmd_output(prun, suggest_filename="pulp-running_tasks")
        self.add_cmd_output(csizes, suggest_filename="mongo-collection_sizes")
        self.add_cmd_output(dbstats, suggest_filename="mongo-db_stats")
        self.add_cmd_output([
            "qpid-stat -%s --ssl-certificate=%s -b amqps://localhost:5671" %
            (opt, self.messaging_cert_file) for opt in "quc"
        ])
        self.add_cmd_output(
            "sudo -u pulp PULP_SETTINGS='/etc/pulp/settings.py' "
            "DJANGO_SETTINGS_MODULE='pulpcore.app.settings' dynaconf list",
            suggest_filename="dynaconf_list"
        )

    def build_mongo_cmd(self, query):
        _cmd = "bash -c %s"
        _mondb = "--host %s --port %s %s %s" % (self.dbhost, self.dbport,
                                                self.dbuser, self.dbpassword)
        _moncmd = "mongo pulp_database %s --eval %s"
        return _cmd % quote(_moncmd % (_mondb, query))

    def postproc(self):

        # Handle all ".conf" files under /etc/pulp - note that this includes
        # files nested at several distinct directory levels. For this reason we
        # use a regex that matches all these path components with ".*", and
        # ensure that the path ends with ".conf".
        etcreg = r"(([a-z].*(passw|token|cred|secret).*)\:(\s))(.*)"
        repl = r"\1 ********"
        self.do_path_regex_sub(r"/etc/pulp/(.*)\.conf$", etcreg, repl)

        # Now handle JSON-formatted data in the same /etc/pulp directory
        # structure. We use a different substitution string here to preserve
        # the file's JSON syntax.
        jreg = r"(\s*\".*(passw|cred|token|secret).*\"\s*:(\s))(.*)(\w+)"
        repl = r"\1********"
        self.do_path_regex_sub("/etc/pulp(.*)(.json$)", jreg, repl)

        # obfuscate SECRET_KEY = .. and 'PASSWORD': .. in dynaconf list output
        # and also in settings.py
        # count with option that PASSWORD is with(out) quotes or in capitals
        key_pass_re = r"(SECRET_KEY\s*=|(password|PASSWORD)(\"|'|:)+)\s*(\S*)"
        repl = r"\1 ********"
        self.do_path_regex_sub("/etc/pulp/settings.py", key_pass_re, repl)
        self.do_cmd_output_sub("dynaconf list", key_pass_re, repl)

# vim: set et ts=4 sw=4 :
