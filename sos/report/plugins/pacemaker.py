# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)
from datetime import datetime, timedelta
import re


class Pacemaker(Plugin):

    short_desc = 'Pacemaker high-availability cluster resource manager'

    plugin_name = "pacemaker"
    profiles = ("cluster", )
    packages = (
        "pacemaker",
        "pacemaker-remote",
    )

    option_list = [
        PluginOpt('crm_from', default='', val_type=str,
                  desc='specfiy the start time for crm_report'),
        PluginOpt('crm_scrub', default=True,
                  desc='enable crm_report password scrubbing')
    ]

    envfile = ""

    def setup_crm_mon(self):
        self.add_cmd_output("crm_mon -1 -A -n -r -t")

    def setup_crm_shell(self):
        self.add_cmd_output([
            "crm status",
            "crm configure show",
        ])

    def setup_pcs(self):
        self.add_copy_spec("/var/log/pcsd/pcsd.log")
        self.add_cmd_output([
            "pcs config",
            "pcs status --full",
            "pcs stonith sbd status --full",
            "pcs stonith sbd watchdog list",
            "pcs stonith history show",
            "pcs quorum status",
            "pcs property list --all"
        ])

    def postproc_crm_shell(self):
        self.do_cmd_output_sub(
            "crm configure show",
            r"passw([^\s=]*)=\S+",
            r"passw\1=********"
        )

    def postproc_pcs(self):
        self.do_cmd_output_sub(
            "pcs config",
            r"passw([^\s=]*)=\S+",
            r"passw\1=********"
        )

    def setup(self):
        self.add_copy_spec([
            # Pacemaker 2.x default log locations
            "/var/log/pacemaker/pacemaker.log*",
            "/var/log/pacemaker/bundles/*/",
            "/var/log/pacemaker/pengine*",

            # Pacemaker 1.x default log locations
            "/var/log/pacemaker.log",
            "/var/log/pacemaker/bundles/*/",

            # Common user-specified locations
            "/var/log/cluster/pacemaker.log*",
            "/var/log/cluster/bundles/*/",
        ])

        self.setup_crm_mon()

        # crm_report needs to be given a --from "YYYY-MM-DD HH:MM:SS" start
        # time in order to collect data.
        crm_from = (datetime.today() -
                    timedelta(hours=72)).strftime("%Y-%m-%d %H:%m:%S")
        if self.get_option("crm_from"):
            if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
                        str(self.get_option("crm_from"))):
                crm_from = self.get_option("crm_from")
            else:
                self._log_error(
                    "crm_from parameter '%s' is not a valid date: using "
                    "default" % self.get_option("crm_from"))

        crm_dest = self.get_cmd_output_path(name="crm_report", make=False)
        if self.get_option("crm_scrub"):
            crm_scrub = '-p "passw.*"'
        else:
            crm_scrub = ""
            self._log_warn("scrubbing of crm passwords has been disabled:")
            self._log_warn("data collected by crm_report may contain"
                           " sensitive values.")
        self.add_cmd_output('crm_report --sos-mode %s -S -d '
                            ' --dest %s --from "%s"' %
                            (crm_scrub, crm_dest, crm_from),
                            chroot=self.tmp_in_sysroot())

        # collect user-defined logfiles, matching a shell-style syntax:
        #   PCMK_logfile=filename
        # specified in the pacemaker start-up environment file.
        pattern = r'^\s*PCMK_logfile=[\'\"]?(\S+)[\'\"]?\s*(\s#.*)?$'
        if self.path_isfile(self.envfile):
            self.add_copy_spec(self.envfile)
            with open(self.envfile) as f:
                for line in f:
                    if re.match(pattern, line):
                        # remove trailing and leading quote marks, in case the
                        # line is e.g. PCMK_logfile="/var/log/pacemaker.log"
                        logfile = re.search(pattern, line).group(1)
                        for regexp in [r'^"', r'"$', r'^\'', r'\'$']:
                            logfile = re.sub(regexp, '', logfile)
                        self.add_copy_spec(logfile)


class DebianPacemaker(Pacemaker, DebianPlugin, UbuntuPlugin):
    def setup(self):
        self.envfile = self.path_join("/etc/default/pacemaker")
        self.setup_crm_shell()
        self.setup_pcs()
        super(DebianPacemaker, self).setup()

    def postproc(self):
        self.postproc_crm_shell()
        self.postproc_pcs()


class RedHatPacemaker(Pacemaker, RedHatPlugin):
    def setup(self):
        self.envfile = self.path_join("/etc/sysconfig/pacemaker")
        self.setup_pcs()
        self.add_copy_spec("/etc/sysconfig/sbd")
        super(RedHatPacemaker, self).setup()

    def postproc(self):
        self.postproc_pcs()

# vim: et ts=4 sw=4
