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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from datetime import datetime, timedelta
import re


class Pacemaker(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """HA Cluster resource manager"""

    plugin_name = "pacemaker"
    profiles = ("cluster", )
    packages = ["pacemaker"]

    option_list = [
        ("crm_from", "specify the start time for crm_report", "fast", False),
        ("crm_scrub", "enable password scrubbing for crm_report", "", True),
    ]

    def setup(self):
        self.add_copy_spec([
            "/var/lib/pacemaker/cib/cib.xml",
            "/etc/sysconfig/pacemaker",
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
        self.add_cmd_output('crm_report %s -S -d --dest %s --from "%s"' %
                            (crm_scrub, crm_dest, crm_from),
                            chroot=self.tmp_in_sysroot())
# vim: et ts=4 sw=4
