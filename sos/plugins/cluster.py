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
import os.path
from glob import glob
from datetime import datetime, timedelta


class Cluster(Plugin, RedHatPlugin):
    """Red Hat Cluster High Availability and GFS2
    """

    plugin_name = 'cluster'
    profiles = ('cluster',)

    option_list = [
        ("gfs2lockdump", 'gather output of gfs2 lockdumps', 'slow', False),
        ("crm_from", 'specify the start time for crm_report', 'fast', False),
        ('lockdump', 'gather dlm lockdumps', 'slow', False),
        ('crm_scrub', 'enable password scrubbing for crm_report', '', True),
    ]

    packages = [
        "luci",
        "ricci",
        "corosync",
        "openais",
        "cman",
        "clusterlib",
        "fence-agents",
        "pacemaker"
    ]

    files = ["/etc/cluster/cluster.conf"]

    debugfs_path = "/sys/kernel/debug"
    _debugfs_cleanup = False

    def setup(self):

        self.add_copy_spec([
            "/etc/cluster.conf",
            "/etc/cluster",
            "/etc/sysconfig/dlm",
            "/etc/sysconfig/pacemaker",
            "/etc/sysconfig/cluster",
            "/etc/sysconfig/cman",
            "/etc/fence_virt.conf",
            "/var/lib/ricci",
            "/var/lib/luci/data/luci.db",
            "/var/lib/luci/etc",
            "/var/log/cluster",
            "/var/log/luci",
            "/sys/fs/gfs2/*/withdraw"
        ])

        if self.get_option('gfs2lockdump'):
            if self._mount_debug():
                self.add_copy_spec(["/sys/kernel/debug/gfs2/*"])

        if self.get_option('lockdump'):
            self.do_lockdump()

        self.add_cmd_output([
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
            "gfs_control ls -n",
            "gfs_control dump",
            "fence_tool dump",
            "dlm_tool dump",
            "dlm_tool ls -n",
            "mkqdisk -L",
            "pcs config",
            "pcs status",
            "pcs property list --all"
        ])

        # crm_report needs to be given a --from "YYYY-MM-DD HH:MM:SS" start
        # time in order to collect data.
        crm_from = (datetime.today() -
                    timedelta(hours=72)).strftime("%Y-%m-%d %H:%m:%S")
        if self.get_option('crm_from') is not False:
            if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
                        str(self.get_option('crm_from'))):
                crm_from = self.get_option('crm_from')
            else:
                self._log_error(
                    "crm_from parameter '%s' is not a valid date: using "
                    "default" % self.get_option('crm_from'))

        crm_dest = self.get_cmd_output_path(name='crm_report', make=False)
        crm_scrub = '-p "passw.*"'
        if not self.get_option("crm_scrub"):
            crm_scrub = ''
            self._log_warn("scrubbing of crm passwords has been disabled:")
            self._log_warn("data collected by crm_report may contain"
                           " sensitive values.")
        self.add_cmd_output('crm_report %s -S -d --dest %s --from "%s"' %
                            (crm_scrub, crm_dest, crm_from),
                            chroot=self.tmp_in_sysroot())

    def do_lockdump(self):
        if self._mount_debug():
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

    def _mount_debug(self):
        if not os.path.ismount(self.debugfs_path):
            self._debugfs_cleanup = True
            r = self.call_ext_prog("mount -t debugfs debugfs %s"
                                   % self.debugfs_path)
            if r['status'] != 0:
                self._log_error("debugfs not mounted and mount attempt failed")
                self._debugfs_cleanup = False
        return os.path.ismount(self.debugfs_path)

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
        if self._debugfs_cleanup and os.path.ismount(self.debugfs_path):
            r = self.call_ext_prog("umount %s" % self.debugfs_path)
            if r['status'] != 0:
                self._log_error("could not unmount %s" % self.debugfs_path)

        return

# vim: set et ts=4 sw=4 :
