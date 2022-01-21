# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker  <jhunsake@redhat.com>
# Copyright (C) 2013 Red Hat, Inc., Lukas Zapletal <lzap@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, SCLPlugin,
                                DebianPlugin, UbuntuPlugin, PluginOpt)
from pipes import quote
from re import match
from sos.utilities import is_executable


class Foreman(Plugin):

    short_desc = 'Foreman/Satellite systems management'

    plugin_name = 'foreman'
    plugin_timeout = 1800
    profiles = ('sysmgmt',)
    packages = ('foreman',)
    option_list = [
        PluginOpt('months', default=1,
                  desc='number of months for dynflow output'),
        PluginOpt('proxyfeatures', default=False,
                  desc='collect features of smart proxies'),
        PluginOpt('puma-gc', default=False,
                  desc='collect Puma GC stats')
    ]
    pumactl = 'pumactl %s -S /usr/share/foreman/tmp/puma.state'

    def setup(self):
        # for external DB, search in /etc/foreman/database.yml for:
        # production:
        # ..
        #   host: some.hostname
        production_scope = False
        self.dbhost = "localhost"
        self.dbpasswd = ""
        try:
            for line in open("/etc/foreman/database.yml").read().splitlines():
                # skip empty lines and lines with comments
                if not line or line[0] == '#':
                    continue
                if line.startswith("production:"):
                    production_scope = True
                    continue
                if production_scope and match(r"\s+host:\s+\S+", line):
                    self.dbhost = line.split()[1]
                if production_scope and match(r"\s+password:\s+\S+", line):
                    self.dbpasswd = line.split()[1]
                # if line starts with a text, it is a different scope
                if not line.startswith(" "):
                    production_scope = False
        except IOError:
            # fallback when the cfg file is not accessible
            pass
        # strip wrapping ".." or '..' around password
        if (self.dbpasswd.startswith('"') and self.dbpasswd.endswith('"')) or \
           (self.dbpasswd.startswith('\'') and self.dbpasswd.endswith('\'')):
            self.dbpasswd = self.dbpasswd[1:-1]
        # set the password to os.environ when calling psql commands to prevent
        # printing it in sos logs
        # we can't set os.environ directly now: other plugins can overwrite it
        self.env = {"PGPASSWORD": self.dbpasswd}

        self.add_file_tags({
            '/var/log/foreman/production.log.*': 'foreman_production_log',
            '/etc/sysconfig/foreman-tasks': 'foreman_tasks_config',
            '/etc/sysconfig/dynflowd': 'foreman_tasks_config'
        })

        self.add_forbidden_path([
            "/etc/foreman/*key.pem",
            "/etc/foreman/encryption_key.rb"
        ])

        _hostname = self.exec_cmd('hostname')['output']
        _hostname = _hostname.strip()
        _host_f = self.exec_cmd('hostname -f')['output']
        _host_f = _host_f.strip()

        # Collect these completely everytime
        self.add_copy_spec([
            "/var/log/foreman/production.log",
            "/var/log/{}*/foreman-ssl_*_ssl.log".format(self.apachepkg)
        ], sizelimit=0)

        # Allow limiting these
        self.add_copy_spec([
            "/etc/foreman/",
            "/etc/sysconfig/foreman",
            "/etc/sysconfig/dynflowd",
            "/etc/default/foreman",
            "/var/log/foreman/dynflow_executor*log*",
            "/var/log/foreman/dynflow_executor*.output*",
            "/var/log/foreman/apipie_cache*.log*",
            "/var/log/foreman/cron*.log*",
            "/var/log/foreman/db_migrate*log*",
            "/var/log/foreman/db_seed*log*",
            "/var/log/foreman/production.log[.-]*",
            "/var/log/foreman-selinux-install.log",
            "/var/log/foreman-proxy-certs-generate*",
            "/usr/share/foreman/Gemfile*",
            "/var/log/{}*/foreman*".format(self.apachepkg),
            "/var/log/{}*/katello-reverse-proxy_access_ssl.log*".format(
                self.apachepkg),
            "/var/log/{}*/katello-reverse-proxy_error_ssl.log*".format(
                self.apachepkg),
            "/var/log/{}*/error_log*".format(self.apachepkg),
            "/etc/{}*/conf/".format(self.apachepkg),
            "/etc/{}*/conf.d/".format(self.apachepkg)
        ])

        self.add_cmd_output([
            'hammer ping',
            'foreman-selinux-relabel -nv',
            'passenger-status --show pool',
            'passenger-status --show requests',
            'passenger-status --show backtraces',
            'passenger-memory-stats',
            'ls -lanR /root/ssl-build',
            'ls -lanR /usr/share/foreman/config/hooks',
            'ping -c1 -W1 %s' % _hostname,
            'ping -c1 -W1 %s' % _host_f,
            'ping -c1 -W1 localhost'
        ])

        # Dynflow Sidekiq
        self.add_cmd_output('systemctl list-units dynflow*',
                            suggest_filename='dynflow_units')
        self.add_service_status('"system-dynflow\\x2dsidekiq.slice"',
                                suggest_filename='dynflow_sidekiq_status')
        self.add_journal(units="dynflow-sidekiq@*")

        # Puma stats & status, i.e. foreman-puma-stats, then
        # pumactl stats -S /usr/share/foreman/tmp/puma.state
        # and optionally also gc-stats
        # if on RHEL with Software Collections, wrap the commands accordingly
        if self.get_option('puma-gc'):
            self.add_cmd_output(self.pumactl % 'gc-stats',
                                suggest_filename='pumactl_gc-stats')
        self.add_cmd_output(self.pumactl % 'stats',
                            suggest_filename='pumactl_stats')
        self.add_cmd_output('/usr/sbin/foreman-puma-status')

        # collect tables sizes, ordered
        _cmd = self.build_query_cmd(
            "SELECT table_name, pg_size_pretty(total_bytes) AS total, "
            "pg_size_pretty(index_bytes) AS INDEX , "
            "pg_size_pretty(toast_bytes) AS toast, pg_size_pretty(table_bytes)"
            " AS TABLE FROM ( SELECT *, "
            "total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes "
            "FROM (SELECT c.oid,nspname AS table_schema, relname AS "
            "TABLE_NAME, c.reltuples AS row_estimate, "
            "pg_total_relation_size(c.oid) AS total_bytes, "
            "pg_indexes_size(c.oid) AS index_bytes, "
            "pg_total_relation_size(reltoastrelid) AS toast_bytes "
            "FROM pg_class c LEFT JOIN pg_namespace n ON "
            "n.oid = c.relnamespace WHERE relkind = 'r') a) a order by "
            "total_bytes DESC"
        )
        self.add_cmd_output(_cmd, suggest_filename='foreman_db_tables_sizes',
                            env=self.env)

        months = '%s months' % self.get_option('months')

        # Construct the DB queries, using the months option to limit the range
        # of entries returned

        scmd = (
            "select id,name,value from settings where name not similar to "
            "'%(pass|key|secret)%'"
        )

        authcmd = (
            'select type,name,host,port,account,base_dn,attr_login,'
            'onthefly_register,tls from auth_sources'
        )

        dyncmd = (
            'select dynflow_execution_plans.* from foreman_tasks_tasks join '
            'dynflow_execution_plans on (foreman_tasks_tasks.external_id = '
            'dynflow_execution_plans.uuid::varchar) where foreman_tasks_tasks.'
            'started_at > NOW() - interval %s' % quote(months)
        )

        dactioncmd = (
             'select dynflow_actions.* from foreman_tasks_tasks join '
             'dynflow_actions on (foreman_tasks_tasks.external_id = '
             'dynflow_actions.execution_plan_uuid::varchar) where '
             'foreman_tasks_tasks.started_at > NOW() - interval %s'
             % quote(months)
        )

        dstepscmd = (
            'select dynflow_steps.* from foreman_tasks_tasks join '
            'dynflow_steps on (foreman_tasks_tasks.external_id = '
            'dynflow_steps.execution_plan_uuid::varchar) where '
            'foreman_tasks_tasks.started_at > NOW() - interval %s'
            % quote(months)
        )

        # counts of fact_names prefixes/types: much of one type suggests
        # performance issues
        factnamescmd = (
            'WITH prefix_counts AS (SELECT split_part(name,\'::\',1) FROM '
            'fact_names) SELECT COUNT(*), split_part AS "fact_name_prefix" '
            'FROM prefix_counts GROUP BY split_part ORDER BY count DESC '
            'LIMIT 100'
        )

        # Populate this dict with DB queries that should be saved directly as
        # postgres formats them. The key will be the filename in the foreman
        # plugin directory, with the value being the DB query to run

        foremandb = {
            'foreman_settings_table': scmd,
            'foreman_auth_table': authcmd,
            'dynflow_schema_info': 'select * from dynflow_schema_info',
            'audits_table_count': 'select count(*) from audits',
            'logs_table_count': 'select count(*) from logs',
            'fact_names_prefixes': factnamescmd,
            'smart_proxies': 'select name,url,download_policy ' +
                             'from smart_proxies'
        }

        # Same as above, but tasks should be in CSV output

        foremancsv = {
            'foreman_tasks_tasks': 'select * from foreman_tasks_tasks',
            'dynflow_execution_plans': dyncmd,
            'dynflow_actions': dactioncmd,
            'dynflow_steps': dstepscmd,
        }

        for table in foremandb:
            _cmd = self.build_query_cmd(foremandb[table])
            self.add_cmd_output(_cmd, suggest_filename=table, timeout=600,
                                sizelimit=100, env=self.env)

        # dynflow* tables on dynflow >=1.6.3 are encoded and hence in that
        # case, psql-msgpack-decode wrapper tool from dynflow-utils (any
        # version) must be used instead of plain psql command
        dynutils = self.is_installed('dynflow-utils')
        for dyn in foremancsv:
            binary = "psql"
            if dyn != 'foreman_tasks_tasks' and dynutils:
                binary = "/usr/libexec/psql-msgpack-decode"
            _cmd = self.build_query_cmd(foremancsv[dyn], csv=True,
                                        binary=binary)
            self.add_cmd_output(_cmd, suggest_filename=dyn, timeout=600,
                                sizelimit=100, env=self.env)

        if self.get_option('proxyfeatures'):
            # get a list of proxy names and URLs, and query for their features
            # store results in smart_proxies_features subdirectory
            _cmd = self.build_query_cmd('select name,url from smart_proxies',
                                        csv=True)
            proxies = self.exec_cmd(_cmd, env=self.env)
            if proxies['status'] == 0:
                # output contains header as the first line, skip it
                for proxy in proxies['output'].splitlines()[1:]:
                    proxy = proxy.split(',')
                    # proxy is now tuple [name, url]
                    _cmd = 'curl -s --key /etc/foreman/client_key.pem ' \
                           '--cert /etc/foreman/client_cert.pem ' \
                           '%s/v2/features' % proxy[1]
                    self.add_cmd_output(_cmd, suggest_filename=proxy[0],
                                        subdir='smart_proxies_features',
                                        timeout=10)

        # collect http[|s]_proxy env.variables
        self.add_env_var(["http_proxy", "https_proxy"])

    def build_query_cmd(self, query, csv=False, binary="psql"):
        """
        Builds the command needed to invoke the pgsql query as the postgres
        user.
        The query requires significant quoting work to satisfy both the
        shell and postgres parsing requirements. Note that this will generate
        a large amount of quoting in sos logs referencing the command being run
        """
        if csv:
            query = "COPY (%s) TO STDOUT " \
                    "WITH (FORMAT 'csv', DELIMITER ',', HEADER)" % query
        _dbcmd = "%s --no-password -h %s -p 5432 -U foreman -d foreman -c %s"
        return _dbcmd % (binary, self.dbhost, quote(query))

    def postproc(self):
        self.do_path_regex_sub(
            "/var/log/%s*/foreman-ssl_access_ssl.log*" % self.apachepkg,
            r"(.*\?(passw|cred|token|secret|key).*=)(.*) (HTTP.*(.*))",
            r"\1******** \4")
        self.do_path_regex_sub(
            r"/etc/foreman/(.*)((conf)(.*)?)",
            r"((\:|\s*)(passw|cred|token|secret|key).*(\:\s|=))(.*)",
            r"\1********")
        # yaml values should be alphanumeric
        self.do_path_regex_sub(
            r"/etc/foreman/(.*)((yaml|yml)(.*)?)",
            r"((\:|\s*)(passw|cred|token|secret|key).*(\:\s|=))(.*)",
            r'\1"********"')

# Let the base Foreman class handle the string substitution of the apachepkg
# attr so we can keep all log definitions centralized in the main class


class RedHatForeman(Foreman, SCLPlugin, RedHatPlugin):

    apachepkg = 'httpd'

    def setup(self):

        self.add_file_tags({
            '/usr/share/foreman/.ssh/ssh_config': 'ssh_foreman_config',
        })
        # if we are on RHEL7 with scl, wrap some Puma commands by
        # scl enable tfm 'command'
        if self.policy.dist_version() == 7 and is_executable('scl'):
            self.pumactl = "scl enable tfm '%s'" % self.pumactl

        super(RedHatForeman, self).setup()
        self.add_cmd_output_scl('tfm', 'gem list',
                                suggest_filename='scl enable tfm gem list')


class DebianForeman(Foreman, DebianPlugin, UbuntuPlugin):

    apachepkg = 'apache2'

# vim: set et ts=4 sw=4 :
