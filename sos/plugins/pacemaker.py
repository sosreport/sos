# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from datetime import datetime, timedelta
import re
import os.path


class Pacemaker(Plugin, DebianPlugin, UbuntuPlugin):
    """HA Cluster resource manager"""

    plugin_name = "pacemaker"
    profiles = ("cluster", )
    packages = ["pacemaker"]
    defaults = "/etc/default/pacemaker"

    option_list = [
        ("crm_from", "specify the start time for crm_report", "fast", False),
        ("crm_scrub", "enable password scrubbing for crm_report", "", True),
    ]

    def setup(self):
        self.add_copy_spec([
            "/var/lib/pacemaker/cib/cib.xml",
            self.defaults,
            "/var/log/pacemaker.log",
            "/var/log/pcsd/pcsd.log"
        ])
        self.add_cmd_output([
            "crm_mon -1 -A -n -r -t",
            "crm status",
            "crm configure show",
            "pcs config",
            "pcs status",
            "pcs property list --all"
        ])

        # crm_report needs to be given a --from "YYYY-MM-DD HH:MM:SS" start
        # time in order to collect data.
        crm_from = (datetime.today() -
                    timedelta(hours=72)).strftime("%Y-%m-%d %H:%m:%S")
        if self.get_option("crm_from") is not False:
            if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
                        str(self.get_option("crm_from"))):
                crm_from = self.get_option("crm_from")
            else:
                self._log_error(
                    "crm_from parameter '%s' is not a valid date: using "
                    "default" % self.get_option("crm_from"))

        crm_dest = self.get_cmd_output_path(name="crm_report", make=False)
        crm_scrub = '-p "passw.*"'
        if not self.get_option("crm_scrub"):
            crm_scrub = ""
            self._log_warn("scrubbing of crm passwords has been disabled:")
            self._log_warn("data collected by crm_report may contain"
                           " sensitive values.")
        self.add_cmd_output('crm_report --sos-mode %s -S -d '
                            ' --dest %s --from "%s"' %
                            (crm_scrub, crm_dest, crm_from),
                            chroot=self.tmp_in_sysroot())

        # collect user-defined logfiles, matching pattern:
        # PCMK_loggfile=filename
        # specified in the pacemaker defaults file.
        pattern = '^\s*PCMK_logfile=[\'\"]?(\S+)[\'\"]?\s*(\s#.*)?$'
        if os.path.isfile(self.defaults):
            with open(self.defaults) as f:
                for line in f:
                    if re.match(pattern, line):
                        # remove trailing and leading quote marks, in case the
                        # line is e.g. PCMK_logfile="/var/log/pacemaker.log"
                        logfile = re.search(pattern, line).group(1)
                        for regexp in [r'^"', r'"$', r'^\'', r'\'$']:
                            logfile = re.sub(regexp, '', logfile)
                        self.add_copy_spec(logfile)

    def postproc(self):
        self.do_cmd_output_sub(
            "pcs config",
            r"(passwd=|incoming_password=)\S+",
            r"\1********"
        )


class RedHatPacemaker(Pacemaker, RedHatPlugin):
    """ Handle alternate location of pacemaker defaults file.
    """
    def setup(self):
        self.defaults = "/etc/sysconfig/pacemaker"
        super(RedHatPacemaker, self).setup()


# vim: et ts=4 sw=4
