### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import re, os
from glob import glob
from datetime import datetime, timedelta

class Cluster(Plugin, RedHatPlugin):
    """cluster suite and GFS related information
    """

    plugin_name = 'cluster'
    option_list = [("gfslockdump", 'gather output of gfs lockdumps', 'slow', False),
                    ("crm_from", 'specify the --from parameter passed to crm_report', 'fast', False),
                    ('lockdump', 'gather dlm lockdumps', 'slow', False)]

    packages = [
        "ricci",
        "corosync",
        "openais",
        "cman",
        "clusterlib",
        "fence-agents",
        "pacemaker"
    ]

    files = [ "/etc/cluster/cluster.conf" ]

    def setup(self):

        self.add_copy_spec("/etc/cluster.conf")
        self.add_copy_spec("/etc/cluster.xml")
        self.add_copy_spec("/etc/cluster")
        self.add_copy_spec("/etc/sysconfig/cluster")
        self.add_copy_spec("/etc/sysconfig/cman")
        self.add_copy_spec("/etc/fence_virt.conf")
        self.add_copy_spec("/var/lib/ricci")
        self.add_copy_spec("/var/lib/luci/data/luci.db")
        self.add_copy_spec("/var/lib/luci/etc")
        self.add_copy_spec("/var/log/cluster")
        self.add_copy_spec("/var/log/luci")
        self.add_copy_spec("/etc/fence_virt.conf")

        if self.get_option('gfslockdump'):
            self.do_gfslockdump()

        if self.get_option('lockdump'):
            self.do_lockdump()

        self.add_cmd_output("rg_test test "
                            + "/etc/cluster/cluster.conf" )
        self.add_cmd_output("fence_tool ls -n")
        self.add_cmd_output("gfs_control ls -n")
        self.add_cmd_output("dlm_tool log_plock")

        self.get_cmd_output_now("clustat")
        self.get_cmd_output_now("group_tool dump")
        self.add_cmd_output("cman_tool services")
        self.add_cmd_output("cman_tool nodes")
        self.add_cmd_output("cman_tool status")
        self.add_cmd_output("ccs_tool lsnode")
        self.add_cmd_output("ipvsadm -L")

        self.add_cmd_output("corosync-quorumtool -l")
        self.add_cmd_output("corosync-quorumtool -s")
        self.add_cmd_output("corosync-cpgtool")
        self.add_cmd_output("corosync-objctl")
        self.add_cmd_output("group_tool ls -g1")
        self.add_cmd_output("gfs_control ls -n")
        self.add_cmd_output("gfs_control dump")
        self.add_cmd_output("fence_tool dump")
        self.add_cmd_output("dlm_tool dump")
        self.add_cmd_output("dlm_tool ls -n")
        self.add_cmd_output("mkqdisk -L")
        # crm_report needs to be given a --from "YYYY-MM-DD HH:MM:SS" start
        # time in order to collect data.
        crm_from = (datetime.today()
                    - timedelta(hours=72)).strftime("%Y-%m-%d %H:%m:%S")
        if self.get_option('crm_from') != False:
            if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
                        str(self.getOption('crm_from'))):
                crm_from = self.getOption('crm_from')
            else:
                self.soslog.error("crm_from parameter '%s' is not a valid date"
                            % self.getOption('crm_from'))

        crm_dest = os.path.join(self.get_cmd_dir(), 'crm_report')
        self.add_cmd_output('crm_report -S -d --dest %s --from "%s"'
                    % (crm_dest, crm_from))

    def do_lockdump(self):
        status, output, time = self.call_ext_prog("dlm_tool ls")
        for lockspace in re.compile(r'^name\s+([^\s]+)$',
                re.MULTILINE).findall(output):
            self.add_cmd_output("dlm_tool lockdebug -svw '%s'" % lockspace,
                        suggest_filename = "dlm_locks_%s" % lockspace)

    def do_gfslockdump(self):
        for mntpoint in self.do_regex_find_all(r'^\S+\s+([^\s]+)\s+gfs\s+.*$',
                    "/proc/mounts"):
            self.add_cmd_output("gfs_tool lockdump %s" % mntpoint,
                        suggest_filename = "gfs_lockdump_"
                        + self.mangle_command(mntpoint))

    def postproc(self):
        for cluster_conf in glob("/etc/cluster/cluster.conf*"):
            self.do_file_sub(cluster_conf,
                        r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")",
                        r"\1%s" %('"***"'))
        self.do_cmd_output_sub("corosync-objctl",
                        r"(.*fence.*\.passwd=)(.*)",
                        r"\1******")
        return
