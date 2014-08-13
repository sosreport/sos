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

from sos.plugins import Plugin, RedHatPlugin
import re
from glob import glob
from datetime import datetime, timedelta


class Cluster(Plugin, RedHatPlugin):
    """cluster suite and GFS related information
    """

    plugin_name = 'cluster'
    option_list = [
        ("gfslockdump", 'gather output of gfs lockdumps', 'slow', False),
        ("crm_from", 'specify the start time for crm_report', 'fast', False),
        ('lockdump', 'gather dlm lockdumps', 'slow', False)
    ]

    packages = [
        "ricci",
        "corosync",
        "openais",
        "cman",
        "clusterlib",
        "fence-agents",
        "pacemaker"
    ]

    files = ["/etc/cluster/cluster.conf"]

    def setup(self):

        self.add_copy_specs([
            "/etc/cluster.conf",
            "/etc/cluster.xml",
            "/etc/cluster",
            "/etc/sysconfig/cluster",
            "/etc/sysconfig/cman",
            "/etc/fence_virt.conf",
            "/var/lib/ricci",
            "/var/lib/luci/data/luci.db",
            "/var/lib/luci/etc",
            "/var/log/cluster",
            "/var/log/luci",
            "/etc/fence_virt.conf",
            "/sys/fs/gfs2/*/withdraw"
        ])

        if self.get_option('gfslockdump'):
            self.do_gfslockdump()

        if self.get_option('lockdump'):
            self.do_lockdump()

        self.add_cmd_outputs([
            "rg_test test /etc/cluster/cluster.conf",
            "fence_tool ls -n",
            "gfs_control ls -n",
            "dlm_tool log_plock",
            "clustat",
            "group_tool dump",
            "cman_tool services",
            "cman_tool nodes",
            "cman_tool status",
            "ccs_tool lsnode",
            "corosync-quorumtool -l",
            "corosync-quorumtool -s",
            "corosync-cpgtool",
            "corosync-objctl",
            "group_tool ls -g1",
            "gfs_control ls -n",
            "gfs_control dump",
            "fence_tool dump",
            "dlm_tool dump",
            "dlm_tool ls -n",
            "mkqdisk -L"
        ])

        # crm_report needs to be given a --from "YYYY-MM-DD HH:MM:SS" start
        # time in order to collect data.
        crm_from = (datetime.today()
                    - timedelta(hours=72)).strftime("%Y-%m-%d %H:%m:%S")
        if self.get_option('crm_from') is not False:
            if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
                        str(self.get_option('crm_from'))):
                crm_from = self.get_option('crm_from')
            else:
                self._log_error(
                    "crm_from parameter '%s' is not a valid date: using "
                    "default" % self.get_option('crm_from'))

        crm_dest = self.get_cmd_output_path(name='crm_report')
        self.add_cmd_output('crm_report -S -d --dest %s --from "%s"'
                            % (crm_dest, crm_from))

    def do_lockdump(self):
        dlm_tool = "dlm_tool ls"
        result = self.call_ext_prog(dlm_tool)
        if result['status'] != 0:
            return

        lock_exp = r'^name\s+([^\s]+)$'
        lock_re = re.compile(lock_exp, re.MULTILINE)
        for lockspace in lock_re.findall(result['output']):
            self.add_cmd_output(
                "dlm_tool lockdebug -svw '%s'" % lockspace,
                suggest_filename="dlm_locks_%s" % lockspace
            )

    def do_gfslockdump(self):
        mnt_exp = r'^\S+\s+([^\s]+)\s+gfs\s+.*$'
        for mnt in self.do_regex_find_all(mnt_exp, "/proc/mounts"):
            self.add_cmd_output(
                "gfs_tool lockdump %s" % mnt,
                suggest_filename="gfs_lockdump_" + self.mangle_command(mnt)
            )

    def postproc(self):
        for cluster_conf in glob("/etc/cluster/cluster.conf*"):
            self.do_file_sub(
                cluster_conf,
                r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")",
                r"\1%s" % ('"***"')
            )

        self.do_path_regex_sub(
            "/var/lib/luci/etc/.*\.ini",
            r"(.*secret\s*=\s*)\S+",
            r"\1******"
        )

        self.do_cmd_output_sub(
            "corosync-objctl",
            r"(.*fence.*\.passwd=)(.*)",
            r"\1******"
        )
        return

# vim: et ts=4 sw=4
