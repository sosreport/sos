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

import sos.plugintools
import os, re
from glob import glob

class cluster(sos.plugintools.PluginBase):
    """cluster suite and GFS related information
    """

    optionList = [("gfslockdump", 'gather output of gfs lockdumps', 'slow', False),
                  ('lockdump', 'gather dlm lockdumps', 'slow', False)]

    def checkenabled(self):
        rhelver = self.policy().rhelVersion()
        if rhelver == 4:
            self.packages = [ "ccs", "cman", "cman-kernel", "magma", "magma-plugins", 
                              "rgmanager", "fence", "dlm", "dlm-kernel", "gulm",
                              "GFS", "GFS-kernel", "lvm2-cluster" ]
        elif rhelver == 5:
            self.packages = [ "rgmanager", "luci", "ricci", "system-config-cluster",
                              "gfs-utils", "gnbd", "kmod-gfs", "kmod-gnbd", "lvm2-cluster", "gfs2-utils" ]

        elif rhelver == 6:
            self.packages = [ "ricci", "corosync", "openais",
                              "cman", "clusterlib", "fence-agents" ]

        self.files = [ "/etc/cluster/cluster.conf" ]
        return sos.plugintools.PluginBase.checkenabled(self)

    def setup(self):
        rhelver = self.policy().rhelVersion()

        self.addCopySpec("/etc/cluster.conf")
        self.addCopySpec("/etc/cluster.xml")
        self.addCopySpec("/etc/cluster")
        self.addCopySpec("/etc/sysconfig/cluster")
        self.addCopySpec("/etc/sysconfig/cman")
	self.addCopySpec("/etc/fence_virt.conf")
        self.addCopySpec("/var/lib/ricci")
        self.addCopySpec("/var/lib/luci")
        self.addCopySpec("/var/log/cluster")
        self.addCopySpec("/var/log/luci/luci.log")

        if self.getOption('gfslockdump'):
          self.do_gfslockdump()

        if self.getOption('lockdump'):
          self.do_lockdump()

        self.collectExtOutput("/usr/sbin/rg_test test /etc/cluster/cluster.conf")
        self.collectExtOutput("fence_tool ls -n")
        self.collectExtOutput("gfs_control ls -n")
        self.collectExtOutput("dlm_tool log_plock")

        self.collectExtOutput("/sbin/fdisk -l")
        self.collectOutputNow("clustat")
        self.collectOutputNow("group_tool dump")
        self.collectExtOutput("cman_tool services")
        self.collectExtOutput("cman_tool nodes")
        self.collectExtOutput("cman_tool status")
        self.collectExtOutput("ccs_tool lsnode")
        self.collectExtOutput("/sbin/ipvsadm -L")

        if rhelver is 4:
          self.addCopySpec("/proc/cluster/*")
          self.collectExtOutput("cman_tool nodes")
          
        if rhelver is not 4: # 5+
          self.collectExtOutput("cman_tool -a nodes")
        
        if rhelver is 5:
          self.collectExtOutput("group_tool -v")
          self.collectExtOutput("group_tool dump fence")
          self.collectExtOutput("group_tool dump gfs")

        if rhelver not in (4,5): # 6+
          self.collectExtOutput("corosync-quorumtool -l")
          self.collectExtOutput("corosync-quorumtool -s")
          self.collectExtOutput("corosync-cpgtool")
          self.collectExtOutput("corosync-objctl")
          self.collectExtOutput("group_tool ls -g1")
          self.collectExtOutput("gfs_control ls -n")
          self.collectExtOutput("gfs_control dump")
          self.collectExtOutput("fence_tool dump")
          self.collectExtOutput("dlm_tool dump")
          self.collectExtOutput("dlm_tool ls -n")

    def do_lockdump(self):
        rhelver = self.policy().rhelVersion()

        if rhelver is 4:
          status, output, time = self.callExtProg("cman_tool services")
          for lockspace in re.compile(r'^DLM Lock Space:\s*"([^"]*)".*$', re.MULTILINE).findall(output):
              self.callExtProg("echo %s > /proc/cluster/dlm_locks" % lockspace)
              self.collectOutputNow("cat /proc/cluster/dlm_locks",
                  suggest_filename = "dlm_locks_%s" % lockspace)

        if rhelver is 5:
          status, output, time = self.callExtProg("group_tool")
          for lockspace in re.compile(r'^dlm\s+[^\s]+\s+([^\s]+)$', re.MULTILINE).findall(output):
            self.collectExtOutput("dlm_tool lockdebug '%s'" % lockspace,
                suggest_filename = "dlm_locks_%s" % lockspace)

        else: # RHEL6 or recent Fedora
          status, output, time = self.callExtProg("dlm_tool ls")
          for lockspace in re.compile(r'^name\s+([^\s]+)$', re.MULTILINE).findall(output):
            self.collectExtOutput("dlm_tool lockdebug -svw '%s'" % lockspace,
                suggest_filename = "dlm_locks_%s" % lockspace)

    def do_gfslockdump(self):
        for mntpoint in self.doRegexFindAll(r'^\S+\s+([^\s]+)\s+gfs\s+.*$', "/proc/mounts"):
           self.collectExtOutput("/sbin/gfs_tool lockdump %s" % mntpoint,
               suggest_filename = "gfs_lockdump_" + self.mangleCommand(mntpoint))

    def postproc(self):
        for cluster_conf in glob("/etc/cluster/cluster.conf*"):
            self.doRegexSub(cluster_conf, r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")", r"\1%s" %('"***"'))
        return

