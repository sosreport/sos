# Copyright (C) 2018 Red Hat, K.K., Takayoshi Tanaka <tatanaka@redhat.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class MsSQL(Plugin, RedHatPlugin):

    short_desc = 'Microsoft SQL Server on Linux'

    plugin_name = "mssql"
    profiles = ('services',)
    packages = ('mssql-server',)

    option_list = [
        PluginOpt('mssql_conf', default='/var/opt/mssql/mssql.conf',
                  desc='SQL server configuration file')
    ]

    def setup(self):
        mssql_conf = self.get_option('mssql_conf')

        # Pick error log file from mssql_conf.
        # Expecting the following format
        # ```
        # [filelocation]
        # errorlogfile = /var/opt/mssql/log
        # [sqlagent]
        # errorlogfile = /var/opt/mssql/log/sqlagentstartup.log
        # [network]
        # kerberoskeytabfile = /var/opt/mssql/secrets/mssql.keytab
        # ```
        section = ''
        # default values
        errorlogfile = '/var/opt/mssql/log'
        sqlagent_errorlogfile = '/var/opt/mssql/log/sqlagentstartup.log'
        kerberoskeytabfile = None
        try:
            for line in open(mssql_conf).read().splitlines():
                if line.startswith('['):
                    section = line
                    continue
                words = line.split('=')
                if words[0].strip() == 'errorlogfile':
                    if section == '[filelocation]':
                        errorlogfile = words[1].strip()
                    elif section == '[sqlagent]':
                        sqlagent_errorlogfile = words[1].strip()
                elif words[0].strip() == 'kerberoskeytabfile':
                    if section == '[network]':
                        kerberoskeytabfile = words[1].strip()
        except IOError as ex:
            self._log_error('Could not open conf file %s: %s' %
                            (mssql_conf, ex))
            return

        # Collect AD authentication configuratoin
        keytab_err = ('keytab file is specfieid in mssql_conf'
                      ' but not found in %s' % kerberoskeytabfile)
        if kerberoskeytabfile is not None:
            if self.path_isfile(kerberoskeytabfile):
                self.add_cmd_output('ls -l %s' % kerberoskeytabfile)
                self.add_cmd_output('klist -e -k %s' % kerberoskeytabfile)
            else:
                self._log_error(keytab_err)

        # Expecting mssql_conf doesn't includeno sensitive information.
        self.add_copy_spec([
            mssql_conf,
            errorlogfile + '/*',
            sqlagent_errorlogfile
        ])

        if not self.get_option('all_logs'):
            self.add_copy_spec(errorlogfile + '/*')
            self.add_copy_spec(sqlagent_errorlogfile)
        else:
            self.add_copy_spec(errorlogfile + '/*')
            self.add_copy_spec(sqlagent_errorlogfile)

        self.add_journal(units=['mssql-server'])

# vim: set et ts=4 sw=4 :
