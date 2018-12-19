# Copyright (C) 2014 Michele Baldessari <michele at acksyn.org>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin
import os
import os.path
from socket import gethostname


class Pcp(Plugin, RedHatPlugin, DebianPlugin):
    """Performance Co-Pilot data
    """

    plugin_name = 'pcp'
    profiles = ('system', 'performance')
    packages = ('pcp',)

    pcp_conffile = '/etc/pcp.conf'

    # size-limit of PCP logger and manager data collected by default (MB)
    option_list = [
        ("pmmgrlogs", "size-limit in MB of pmmgr logs", "", 100),
        ("pmloggerfiles", "number of newest pmlogger files to grab", "", 12),
    ]

    pcp_sysconf_dir = None
    pcp_var_dir = None
    pcp_log_dir = None

    pcp_hostname = ''

    def get_size(self, path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def pcp_parse_conffile(self):
        try:
            pcpconf = open(self.pcp_conffile, "r")
            lines = pcpconf.readlines()
            pcpconf.close()
        except IOError:
            return False
        env_vars = {}
        for line in lines:
            if line.startswith('#'):
                continue
            try:
                (key, value) = line.strip().split('=')
                env_vars[key] = value
            except (ValueError, KeyError):
                pass

        try:
            self.pcp_sysconf_dir = env_vars['PCP_SYSCONF_DIR']
            self.pcp_var_dir = env_vars['PCP_VAR_DIR']
            self.pcp_log_dir = env_vars['PCP_LOG_DIR']
        except Exception:
            # Fail if all three env variables are not found
            return False

        return True

    def setup(self):
        self.sizelimit = (None if self.get_option("all_logs")
                          else self.get_option("pmmgrlogs"))
        self.countlimit = (None if self.get_option("all_logs")
                           else self.get_option("pmloggerfiles"))

        if not self.pcp_parse_conffile():
            self._log_warn("could not parse %s" % self.pcp_conffile)
            return

        # Add PCP_SYSCONF_DIR (/etc/pcp) and PCP_VAR_DIR (/var/lib/pcp/config)
        # unconditionally. Obviously if someone messes up their /etc/pcp.conf
        # in a ridiculous way (i.e. setting PCP_SYSCONF_DIR to '/') this will
        # break badly.
        var_conf_dir = os.path.join(self.pcp_var_dir, 'config')
        self.add_copy_spec([
            self.pcp_sysconf_dir,
            self.pcp_conffile,
            var_conf_dir
        ])

        # We explicitely avoid /var/lib/pcp/config/{pmchart,pmlogconf,pmieconf,
        # pmlogrewrite} as in 99% of the cases they are just copies from the
        # rpms. It does not make up for a lot of size but it contains many
        # files
        self.add_forbidden_path([
            os.path.join(var_conf_dir, 'pmchart'),
            os.path.join(var_conf_dir, 'pmlogconf'),
            os.path.join(var_conf_dir, 'pmieconf'),
            os.path.join(var_conf_dir, 'pmlogrewrite')
        ])

        # Take PCP_LOG_DIR/pmlogger/`hostname` + PCP_LOG_DIR/pmmgr/`hostname`
        # The *default* directory structure for pmlogger is the following:
        # Dir: PCP_LOG_DIR/pmlogger/HOST/ (we only collect the HOST data
        # itself)
        # - YYYYMMDD.HH.MM.{N,N.index,N.meta} N in [0,1,...]
        # - Latest
        # - pmlogger.{log,log.prior}
        #
        # Can be changed via configuration in PCP_SYSCONF_DIR/pmlogger/control
        # As a default strategy, collect up to 100MB data from each dir.
        # Can be overwritten either via pcp.pcplogsize option or all_logs.
        self.pcp_hostname = gethostname()

        # Make sure we only add the two dirs if hostname is set, otherwise
        # we would collect everything
        if self.pcp_hostname != '':
            # collect pmmgr logs up to 'pmmgrlogs' size limit
            path = os.path.join(self.pcp_log_dir, 'pmmgr',
                                self.pcp_hostname, '*')
            self.add_copy_spec(path, sizelimit=self.sizelimit, tailit=False)
            # collect newest pmlogger logs up to 'pmloggerfiles' count
            files_collected = 0
            path = os.path.join(self.pcp_log_dir, 'pmlogger',
                                self.pcp_hostname, '*')
            pmlogger_ls = self.get_cmd_output_now("ls -t1 %s" % path)
            if pmlogger_ls:
                for line in open(pmlogger_ls).read().splitlines():
                    self.add_copy_spec(line, sizelimit=None)
                    files_collected = files_collected + 1
                    if self.countlimit and files_collected == self.countlimit:
                        break

        self.add_copy_spec([
            # Collect PCP_LOG_DIR/pmcd and PCP_LOG_DIR/NOTICES
            os.path.join(self.pcp_log_dir, 'pmcd'),
            os.path.join(self.pcp_log_dir, 'NOTICES*'),
            # Collect PCP_VAR_DIR/pmns
            os.path.join(self.pcp_var_dir, 'pmns'),
            # Also collect any other log and config files
            # (as suggested by fche)
            os.path.join(self.pcp_log_dir, '*/*.log*'),
            os.path.join(self.pcp_log_dir, '*/*/*.log*'),
            os.path.join(self.pcp_log_dir, '*/*/config*')
        ])

        # Need to get the current status of the PCP infrastructure
        self.add_cmd_output("pcp")
        # Collect a summary for the current day
        res = self.get_command_output('pcp')
        if res['status'] == 0:
            for line in res['output'].splitlines():
                if line.startswith(' pmlogger:'):
                    arc = line.split()[-1]
                    self.add_cmd_output(
                        "pmstat -S 00:00 -T 23:59 -t 5m -x -a %s" % arc,
                        root_symlink="pmstat"
                    )
                    break

# vim: set et ts=4 sw=4 :
