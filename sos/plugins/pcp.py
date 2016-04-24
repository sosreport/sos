# Copyright (C) 2014 Michele Baldessari <michele at acksyn.org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

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

    # size-limit total PCP log data collected by default (MB)
    pcplog_totalsize = 100

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
        except:
            return False
        env_vars = {}
        for line in lines:
            if line.startswith('#'):
                continue
            try:
                (key, value) = line.strip().split('=')
                env_vars[key] = value
            except:
                pass

        try:
            self.pcp_sysconf_dir = env_vars['PCP_SYSCONF_DIR']
            self.pcp_var_dir = env_vars['PCP_VAR_DIR']
            self.pcp_log_dir = env_vars['PCP_LOG_DIR']
        except:
            # Fail if all three env variables are not found
            return False

        return True

    def setup(self):
        if self.get_option("all_logs"):
            self.pcplog_totalsize = 0

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
        self.add_forbidden_path(os.path.join(var_conf_dir, 'pmchart'))
        self.add_forbidden_path(os.path.join(var_conf_dir, 'pmlogconf'))
        self.add_forbidden_path(os.path.join(var_conf_dir, 'pmieconf'))
        self.add_forbidden_path(os.path.join(var_conf_dir, 'pmlogrewrite'))

        # The *default* directory structure for pmlogger is the following:
        # Dir: PCP_LOG_DIR/pmlogger/HOST/ (we only collect the HOST data
        # itself)
        # - YYYYMMDD.HH.MM.{N,N.index,N.meta} N in [0,1,...]
        # - Latest
        # - pmlogger.{log,log.prior}
        #
        # Can be changed via configuration in PCP_SYSCONF_DIR/pmlogger/control
        # As a default strategy, collect PCP_LOG_DIR/pmlogger/* only if the
        # total size is moderately small: < 100MB. Override is possible via
        # the 'all_pcplogs' option.
        # FIXME: Doing a recursive size check because add_copy_spec_limit
        # won't work for directory trees. I.e. we can't say fetch /foo/bar/
        # only if it is < 100MB. To be killed once the Plugin base class will
        # add a method for this use case via issue #281
        self.pcp_hostname = gethostname()

        # Make sure we only add PCP_LOG_DIR/pmlogger/`hostname` if hostname
        # is set, otherwise we'd collect everything
        if self.pcp_hostname != '':
            path = os.path.join(self.pcp_log_dir, 'pmlogger',
                                self.pcp_hostname)
            dirsize = self.get_size(path)
            max_mb_size = self.pcplog_totalsize * 1024 * 1024
            # If explicitely asked collect all logs, otherwise only if < 100MB
            # in total
            if self.pcplog_totalsize == 0 or dirsize < max_mb_size:
                if os.path.isdir(path):
                    self.add_copy_spec(path)
                else:
                    self._log_warn("%s not found" % path)
            else:
                self._log_warn("skipped %s. Size %d bigger than %d"
                               % (path, dirsize, max_mb_size))
        else:
            self._log_warn("pcp_hostname was not set. Skipping.")

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


# vim: set et ts=4 sw=4 :
