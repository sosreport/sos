# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker  <jhunsake@redhat.com>
# Copyright (C) 2013 Red Hat, Inc., Lukas Zapletal <lzap@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin,\
                        SCLPlugin
from pipes import quote


class Foreman(Plugin):
    """Foreman/Satellite 6 systems management
    """

    plugin_name = 'foreman'
    profiles = ('sysmgmt',)
    packages = ('foreman', 'foreman-proxy')
    option_list = [
        ('months', 'number of months for dynflow output', 'fast', 1)
    ]

    def setup(self):
        self.add_forbidden_path([
            "/etc/foreman*/*key.pem",
            "/etc/foreman*/encryption_key.rb"
        ])

        _hostname = self.get_command_output('hostname')['output'].strip()
        _host_f = self.get_command_output('hostname -f')['output'].strip()

        # Collect these completely everytime
        self.add_copy_spec([
            "/var/log/foreman/production.log",
            "/var/log/{}*/foreman-ssl_*_ssl.log".format(self.apachepkg)
        ], sizelimit=0)

        # Allow limiting these
        self.add_copy_spec([
            "/etc/foreman/",
            "/etc/foreman-proxy/",
            "/etc/sysconfig/foreman",
            "/etc/default/foreman",
            "/etc/foreman-installer/",
            "/var/log/foreman/dynflow_executor*log*",
            "/var/log/foreman/dynflow_executor*.output*",
            "/var/log/foreman/apipie_cache*.log*",
            "/var/log/foreman/cron*.log*",
            "/var/log/foreman/db_migrate*log*",
            "/var/log/foreman/db_seed*log*",
            "/var/log/foreman/production.log[.-]*",
            "/var/log/foreman-proxy/cron*log*",
            "/var/log/foreman-proxy/migrate_settings*log*",
            "/var/log/foreman-proxy/proxy*log*",
            "/var/log/foreman-proxy/smart_proxy_dynflow_core*log*",
            "/var/log/foreman-selinux-install.log",
            "/var/log/foreman-proxy-certs-generate*",
            "/var/log/foreman-installer/",
            "/var/log/foreman-maintain/",
            "/var/log/syslog*",
            # Specific to TFM, _all_ catalina logs are relevant. Adding this
            # here rather than the tomcat plugin to ease maintenance and not
            # pollute non-Sat sosreports that enable the tomcat plugin
            "/var/log/tomcat*/catalina*log*",
            "/var/log/tomcat*/host-manager*log*",
            "/var/log/tomcat*/localhost*log*",
            "/var/log/tomcat*/manager*log*",
            "/usr/share/foreman/Gemfile*",
            "/var/lib/puppet/ssl/certs/ca.pem",
            "/etc/puppetlabs/puppet/ssl/certs/ca.pem",
            "/etc/puppetlabs/puppet/ssl/certs/{}.pem".format(_hostname),
            "/var/lib/puppet/ssl/certs/{}.pem".format(_hostname),
            "/var/log/{}*/foreman-ssl_*_ssl*log[.-]*".format(self.apachepkg),
            "/var/log/{}*/error_log*".format(self.apachepkg),
            "/etc/{}*/conf/".format(self.apachepkg),
            "/etc/{}*/conf.d/".format(self.apachepkg)
        ])

        self.add_cmd_output([
            'bundle --local --gemfile=/usr/share/foreman/Gemfile*',
            'hammer ping',
            'foreman-selinux-relabel -nv',
            'foreman-maintain service status',
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
            'dynflow_execution_plans.uuid) where foreman_tasks_tasks.'
            'started_at > NOW() - interval %s' % quote(months)
        )

        dactioncmd = (
             'select dynflow_actions.* from foreman_tasks_tasks join '
             'dynflow_actions on (foreman_tasks_tasks.external_id = '
             'dynflow_actions.execution_plan_uuid) where foreman_tasks_tasks.'
             'started_at > NOW() - interval %s' % quote(months)
        )

        dstepscmd = (
            'select dynflow_steps.* from foreman_tasks_tasks join '
            'dynflow_steps on (foreman_tasks_tasks.external_id = '
            'dynflow_steps.execution_plan_uuid) where foreman_tasks_tasks.'
            'started_at > NOW() - interval %s' % quote(months)
        )

        # Populate this dict with DB queries that should be saved directly as
        # postgres formats them. The key will be the filename in the foreman
        # plugin directory, with the value being the DB query to run

        foremandb = {
            'foreman_settings_table': scmd,
            'foreman_auth_table': authcmd,
            'dynflow_schema_info': 'select * from dynflow_schema_info',
            'foreman_tasks_tasks': 'select * from foreman_tasks_tasks'
        }

        # Same as above, but for CSV output

        foremancsv = {
            'dynflow_execution_plans': dyncmd,
            'dynflow_actions': dactioncmd,
            'dynflow_steps': dstepscmd,
        }

        for table in foremandb:
            _cmd = self.build_query_cmd(foremandb[table])
            self.add_cmd_output(_cmd, suggest_filename=table, timeout=600)

        for dyn in foremancsv:
            _cmd = self.build_query_cmd(foremancsv[dyn], csv=True)
            self.add_cmd_output(_cmd, suggest_filename=dyn, timeout=600)

    def build_query_cmd(self, query, csv=False):
        """
        Builds the command needed to invoke the pgsql query as the postgres
        user.
        The query requires significant quoting work to satisfy both the
        shell and postgres parsing requirements. Note that this will generate
        a large amount of quoting in sos logs referencing the command being run
        """
        _cmd = "su postgres -c %s"
        if not csv:
            _dbcmd = "psql foreman -c %s"
        else:
            _dbcmd = "psql foreman -A -F , -X -c %s"
        dbq = _dbcmd % quote(query)
        return _cmd % quote(dbq)

    def postproc(self):
        satreg = r"((foreman.*)?(\"::(foreman(.*?)|katello).*)?(::(.*)::.*" \
              r"(passw|cred|token|secret|key).*(\")?:))(.*)"
        self.do_path_regex_sub(
            "/var/log/foreman-installer/sat*",
            satreg,
            r"\1 ********")
        # need to do two passes here, debug output has different formatting
        sat_debug_reg = (r"(\s)* (Found key: (\"(foreman(.*?)|katello)"
                         r"::(.*(token|secret|key|passw).*)\") value:) "
                         r"(.*)")
        self.do_path_regex_sub(
            "/var/log/foreman-installer/sat*",
            sat_debug_reg,
            r"\1 \2 ********")
        self.do_path_regex_sub(
            "/var/log/foreman-installer/foreman-proxy*",
            r"(\s*proxy_password\s=) (.*)",
            r"\1 ********")
        self.do_path_regex_sub(
            "/etc/foreman(.*)((yaml|yml|conf)(.*)?)",
            r"((\:|\s*)(passw|cred|token|secret|key).*(\:\s|=))(.*)",
            r"\1********")
        self.do_path_regex_sub(
            "/var/log/foreman-maintain/foreman-maintain.log*",
            r"((passw|cred|token|secret)=)(.*)",
            r"\1********")
        self.do_path_regex_sub(
            "/var/log/%s*/foreman-ssl_access_ssl.log*" % self.apachepkg,
            r"(.*\?(passw|cred|token|secret|key).*=)(.*) (HTTP.*(.*))",
            r"\1******** \4")

# Let the base Foreman class handle the string substitution of the apachepkg
# attr so we can keep all log definitions centralized in the main class


class RedHatForeman(Foreman, SCLPlugin, RedHatPlugin):

    apachepkg = 'httpd'

    def setup(self):
        super(RedHatForeman, self).setup()
        self.add_cmd_output_scl('tfm', 'gem list',
                                suggest_filename='scl enable tfm gem list')


class DebianForeman(Foreman, DebianPlugin, UbuntuPlugin):

    apachepkg = 'apache'

# vim: set et ts=4 sw=4 :
