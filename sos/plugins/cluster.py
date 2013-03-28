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
import os, re
from glob import glob

class cluster(Plugin, RedHatPlugin):
    """cluster suite and GFS related information
    """

    optionList = [("gfslockdump",
                    'gather output of gfs lockdumps', 'slow', False),
                    ('lockdump', 'gather dlm lockdumps', 'slow', False)]

    def check_enabled(self):
        rhelver = self.policy().rhelVersion()
        if rhelver == 4:
            self.packages = [ "ccs", "cman", "cman-kernel", "magma",
                              "magma-plugins", "rgmanager", "fence", "dlm",
                              "dlm-kernel", "gulm", "GFS", "GFS-kernel",
                              "lvm2-cluster" ]
        elif rhelver == 5:
            self.packages = [ "rgmanager", "luci", "ricci",
                              "system-config-cluster", "gfs-utils", "gnbd",
                              "kmod-gfs", "kmod-gnbd", "lvm2-cluster",
                              "gfs2-utils" ]

        elif rhelver == 6:
            self.packages = [ "ricci", "corosync", "openais",
                              "cman", "clusterlib", "fence-agents" ]

        self.files = [ "/etc/cluster/cluster.conf" ]
        return Plugin.check_enabled(self)

    def setup(self):
        rhelver = self.policy().rhelVersion()

        self.add_copy_spec("/etc/cluster.conf")
        self.add_copy_spec("/etc/cluster.xml")
        self.add_copy_spec("/etc/cluster")
        self.add_copy_spec("/etc/sysconfig/cluster")
        self.add_copy_spec("/etc/sysconfig/cman")
        self.add_copy_spec("/etc/fence_virt.conf")
        self.add_copy_spec("/var/lib/ricci")
        self.add_copy_spec("/var/lib/luci")
        self.add_copy_spec("/var/log/cluster")
        self.add_copy_spec("/var/log/luci/luci.log")
        self.add_copy_spec("/etc/fence_virt.conf")

        if self.get_option('gfslockdump'):
          self.do_gfslockdump()

        if self.get_option('lockdump'):
          self.do_lockdump()

        self.add_cmd_output("/usr/sbin/rg_test test "
                        + "/etc/cluster/cluster.conf" )
        self.add_cmd_output("fence_tool ls -n")
        self.add_cmd_output("gfs_control ls -n")
        self.add_cmd_output("dlm_tool log_plock")

        self.add_cmd_output("/sbin/fdisk -l")
        self.get_cmd_output_now("clustat")
        self.get_cmd_output_now("group_tool dump")
        self.add_cmd_output("cman_tool services")
        self.add_cmd_output("cman_tool nodes")
        self.add_cmd_output("cman_tool status")
        self.add_cmd_output("ccs_tool lsnode")
        self.add_cmd_output("/sbin/ipvsadm -L")

        if rhelver is 4:
            self.add_copy_spec("/proc/cluster/*")
            self.add_cmd_output("cman_tool nodes")

        if rhelver is not 4: # 5+
            self.add_cmd_output("cman_tool -a nodes")

        if rhelver is 5:
            self.add_cmd_output("group_tool -v")
            self.add_cmd_output("group_tool dump fence")
            self.add_cmd_output("group_tool dump gfs")

        if rhelver not in (4,5): # 6+
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

    def do_lockdump(self):
        rhelver = self.policy().rhelVersion()

        if rhelver is 4:
            status, output, time = self.call_ext_prog("cman_tool services")
            for lockspace in re.compile(r'^DLM Lock Space:\s*"([^"]*)".*$',
                    re.MULTILINE).findall(output):
                self.call_ext_prog("echo %s > /proc/cluster/dlm_locks" 
                        % lockspace)
                self.get_cmd_output_now("cat /proc/cluster/dlm_locks",
                        suggest_filename = "dlm_locks_%s" % lockspace)

        if rhelver is 5:
            status, output, time = self.call_ext_prog("group_tool")
            for lockspace in re.compile(r'^dlm\s+[^\s]+\s+([^\s]+)$',
                    re.MULTILINE).findall(output):
                self.add_cmd_output("dlm_tool lockdebug '%s'" % lockspace,
                        suggest_filename = "dlm_locks_%s" % lockspace)

        else: # RHEL6 or recent Fedora
            status, output, time = self.call_ext_prog("dlm_tool ls")
            for lockspace in re.compile(r'^name\s+([^\s]+)$',
                    re.MULTILINE).findall(output):
                self.add_cmd_output("dlm_tool lockdebug -svw '%s'"
                        % lockspace,
                        suggest_filename = "dlm_locks_%s" % lockspace)

    def do_gfslockdump(self):
        for mntpoint in self.do_regex_find_all(r'^\S+\s+([^\s]+)\s+gfs\s+.*$',
                    "/proc/mounts"):
            self.add_cmd_output("/sbin/gfs_tool lockdump %s" % mntpoint,
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
