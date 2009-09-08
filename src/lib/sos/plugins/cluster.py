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
import commands, os, re
import time, libxml2

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
                              "gfs-utils", "gnbd", "kmod-gfs", "kmod-gnbd", "lvm2-cluster" ]

        self.files = [ "/etc/cluster/cluster.conf", "/proc/cluster" ]
        return sos.plugintools.PluginBase.checkenabled(self)

    def has_gfs(self):
        return (len(self.doRegexFindAll(r'^\S+\s+\S+\s+gfs\s+.*$', "/etc/mtab")) > 0)

    def diagnose(self):
        rhelver = self.policy().rhelVersion()

        # check if the minimum set of packages is installed
        # for RHEL4 RHCS(ccs, cman, cman-kernel, magma, magma-plugins, (dlm, dlm-kernel) || gulm, perl-Net-Telnet, rgmanager, fence)
        # RHEL4 GFS (GFS, GFS-kernel, ccs, lvm2-cluster, fence)

        pkgs_check = []
        mods_check = []
        serv_check = []

        if rhelver == 4:
            pkgs_check.extend( [ "ccs", "cman", "magma", "magma-plugins", "perl-Net-Telnet", "rgmanager", "fence" ] )
            mods_check.extend( [ "cman", "dlm" ] )
            if self.has_gfs():
                mods_check.append("gfs")
            serv_check.extend( [ "cman", "ccsd", "rgmanager", "fenced" ] )
            if self.has_gfs():
                serv_check.extend( ["gfs", "clvmd"] )
        elif rhelver == 5:
            pkgs_check.extend ( [ "cman", "perl-Net-Telnet", "rgmanager" ] )
            mods_check.extend( [ "dlm" ] )
            if self.has_gfs():
                mods_check.extend( ["gfs", "gfs2"] )
            serv_check.extend( [ "cman", "rgmanager" ] )
            if self.has_gfs():
                serv_check.extend( ["gfs", "clvmd"] )

        # check that kernel module packages are installed for
        # running kernel version

        for modname in mods_check:
           found = 0

           if self.policy().allPkgsByNameRegex( "^" + modname ):
              found = 1

           status, output = commands.getstatusoutput('/sbin/modinfo -F vermagic ' + modname)

           if status == 0:
              found = 2

           if len(self.fileGrep("^%s\s+" % modname, "/proc/modules")) > 0:
              found = 3

           if found == 0:
               self.addDiagnose("required kernel module is missing: %s" % modname)
           elif found == 1:
               self.addDiagnose("required module is not available for current kernel: %s" % modname)
           elif found == 2:
               self.addDiagnose("required module is available but not loaded: %s" % modname)

        for pkg in pkgs_check:
           if not self.isInstalled(pkg):
               self.addDiagnose("required package is missing: %s" % pkg)

        if rhelver == "4":
           # (dlm, dlm-kernel) || gulm
           if not ((self.isInstalled("dlm") and self.isInstalled("dlm-kernel")) or self.isInstalled("gulm")):
               self.addDiagnose("required packages are missing: (dlm, dlm-kernel) || gulm")

        # check if all the needed daemons are active at sosreport time
        # check if they are started at boot time in RHEL4 RHCS (cman, ccsd, rgmanager, fenced)
        # and GFS (gfs, ccsd, clvmd, fenced)

        for service in serv_check:
           status, output = commands.getstatusoutput("/sbin/service %s status &> /dev/null" % service)
           if status != 0:
               self.addDiagnose("service %s is not running" % service)

           if not self.policy().runlevelDefault() in self.policy().runlevelByService(service):
               self.addDiagnose("service %s is not started in default runlevel" % service)

        # FIXME: missing important cman services
        # FIXME: any cman service whose state != run ?
        # Fence Domain:    "default"                           2   2 run       -

        # is cluster quorate
        if not self.is_cluster_quorate():
           self.addDiagnose("cluster node is not quorate")

        # if there is no cluster.conf, diagnose() finishes here.
        try:
           os.stat("/etc/cluster/cluster.conf")
        except:
           self.addDiagnose("/etc/cluster/cluster.conf is missing")
           return

        # setup XML xpath context
        xml = libxml2.parseFile("/etc/cluster/cluster.conf")
        xpathContext = xml.xpathNewContext()

        # make sure that the node names are valid according to RFC 2181
        for hostname in xpathContext.xpathEval('/cluster/clusternodes/clusternode/@name'):
           if not re.match('^[a-zA-Z]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$', hostname.content):
               self.addDiagnose("node name (%s) contains invalid characters" % hostname.content)

        # do not rely on DNS to resolve node names, must have them in /etc/hosts
        for hostname in xpathContext.xpathEval('/cluster/clusternodes/clusternode/@name'):
           if len(self.fileGrep(r'^.*\W+%s' % hostname.content , "/etc/hosts")) == 0:
               self.addDiagnose("node %s is not defined in /etc/hosts" % hostname.content)

        # check fencing (warn on no fencing)
        if len(xpathContext.xpathEval("/cluster/clusternodes/clusternode[not(fence/method/device)]")):
           if self.has_gfs():
               self.addDiagnose("one or more nodes have no fencing agent configured: fencing is required for GFS to work")
           else:
               self.addDiagnose("one or more nodes have no fencing agent configured: the cluster infrastructure might not work as intended")

        # check fencing (warn on manual)
        if len(xpathContext.xpathEval("/cluster/clusternodes/clusternode[/cluster/fencedevices/fencedevice[@agent='fence_manual']/@name=fence/method/device/@name]")):
           self.addDiagnose("one or more nodes have manual fencing agent configured (data integrity is not guaranteed)")

        # if fence_ilo or fence_drac, make sure acpid is not running
        hostname = commands.getoutput("/bin/uname -n").split(".")[0]
        if len(xpathContext.xpathEval('/cluster/clusternodes/clusternode[@name = "%s" and /cluster/fencedevices/fencedevice[@agent="fence_rsa" or @agent="fence_drac"]/@name=fence/method/device/@name]' % hostname )):
           status, output = commands.getstatusoutput("/sbin/service acpid status")
           if status == 0 or self.policy().runlevelDefault() in self.policy().runlevelByService("acpid"):
               self.addDiagnose("acpid is enabled, this may cause problems with your fencing method.")

        # check for fs exported via nfs without nfsid attribute
        if len(xpathContext.xpathEval("/cluster/rm/service//fs[not(@fsid)]/nfsexport")):
           self.addDiagnose("one or more nfs export do not have a fsid attribute set.")

        # cluster.conf file version and the in-memory cluster configuration version matches
        status, cluster_version = commands.getstatusoutput("cman_tool status | grep 'Config version'")
        if not status: cluster_version = cluster_version[16:]
        else: cluster_version = None
        conf_version = xpathContext.xpathEval("/cluster/@config_version")[0].content

        if status == 0 and conf_version != cluster_version:
           self.addDiagnose("cluster.conf and in-memory configuration version differ (%s != %s)" % (conf_version, cluster_version) )

        status, output = commands.getstatusoutput("/usr/sbin/rg_test test /etc/cluster/cluster.conf")
        if output.find("Error: ") > 0:
           self.addDiagnose("configuration errors are present according to rg_test")

        # make sure the first part of the lock table matches the cluster name
        # and that the locking protocol is sane
        cluster_name = xpathContext.xpathEval("/cluster/@name")[0].content

        for fs in self.fileGrep(r'^[^#][/\w]*\W*[/\w]*\W*gfs', "/etc/fstab"):
           # for each gfs entry
           fs = fs.split()
           lockproto = self.get_gfs_sb_field(fs[0], "sb_lockproto")
           if lockproto and lockproto != self.get_locking_proto():
               self.addDiagnose("gfs mountpoint (%s) is using the wrong locking protocol (%s)" % (fs[0], lockproto) )

           locktable = self.get_gfs_sb_field(fs[0], "sb_locktable")
           try: locktable = locktable.split(":")[0]
           except: continue
           if locktable != cluster_name:
               self.addDiagnose("gfs mountpoint (%s) is using the wrong locking table" % fs[0])

    def setup(self):
        self.collectExtOutput("/sbin/fdisk -l")
        self.addCopySpec("/etc/cluster.conf")
        self.addCopySpec("/etc/cluster.xml")
        self.addCopySpec("/etc/cluster")
        self.collectExtOutput("/usr/sbin/rg_test test /etc/cluster/cluster.conf")
        self.addCopySpec("/proc/cluster")
        self.collectExtOutput("cman_tool status")
        self.collectExtOutput("cman_tool services")
        self.collectExtOutput("cman_tool -af nodes")
        self.collectExtOutput("ccs_tool lsnode")
        self.collectExtOutput("openais-cfgtool -s")
        self.collectExtOutput("clustat")

        self.collectExtOutput("/sbin/ipvsadm -L")

        if self.getOption('gfslockdump'): self.do_gfslockdump()
        if self.getOption('lockdump'): self.do_lockdump()

        return

    def do_lockdump(self):
        status, output = commands.getstatusoutput("cman_tool services")
        if status:
            # command somehow failed
            return False

        rhelver = self.get_redhat_release()

        if rhelver == "4":
            regex = r'^DLM Lock Space:\s*"([^"]*)".*$'
        elif rhelver == "5Server" or rhelver == "5Client":
            regex = r'^dlm\s+[^\s]+\s+([^\s]+)\s.*$'

        reg=re.compile(regex,re.MULTILINE)
        for lockspace in reg.findall(output):
           commands.getstatusoutput("echo %s > /proc/cluster/dlm_locks" % lockspace)
           self.collectOutputNow("cat /proc/cluster/dlm_locks", root_symlink = "dlm_locks_%s" % lockspace)

    def get_locking_proto(self):
        # FIXME: what's the best way to find out ?
        return "lock_dlm"
        return "lock_gulm"

    def do_gfslockdump(self):
        for mntpoint in self.doRegexFindAll(r'^\S+\s+([^\s]+)\s+gfs\s+.*$', "/proc/mounts"):
           self.collectExtOutput("/sbin/gfs_tool lockdump %s" % mntpoint, root_symlink = "gfs_lockdump_" + self.mangleCommand(mntpoint) )

    def do_rgmanager_bt(self):
        # FIXME: threads backtrace via SIGALRM
        return

    def postproc(self):
        self.doRegexSub("/etc/cluster/cluster.conf", r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")", r"\1\"***\"")
        return

    def is_cluster_quorate(self):
        output = commands.getoutput("cman_tool status | grep '^Membership state: '")
        try:
            if output[18:] == "Cluster-Member":
                return True
        except:
            pass
        return False

    def get_gfs_sb_field(self, device, field):
        for line in commands.getoutput("/sbin/gfs_tool sb %s all" % device).split("\n"):
            if re.match('^\W*%s = ' % field, line):
                return line.split("=")[1].strip()
        return False
        
    # Diagnostic testing functions
    def test_fence_id(self):
        # resolves rhbz 499468 and 499472
        for line in commands.getoutput("/sbin/group_tool ls | grep -v '^\['").split("\n")[1:]:
            for a in line.split():
                # we can do this since fence id is a fix field
                if re.match('00000000', a):
                    self.addDiagnose('Invalid fence id: %s' % (line,))
            if line.split()[-1] != 'none':
                self.addDiagnose("Possible incorrect state: %s, for group: %s" % (line.split()[-1], line))
        return
