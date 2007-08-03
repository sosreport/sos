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
                  ('lockdump', 'gather dlm lockdumps', 'slow', False),
                  ('taskdump', 'trigger 3 sysrq+t dumps every 5 seconds (dangerous)', 'slow', False)]

    def checkenabled(self):
       # enable if any related package is installed
       for pkg in [ "ccs", "cman", "cman-kernel", "magma", "magma-plugins", 
		    "rgmanager", "fence", "dlm", "dlm-kernel", "gulm",
		    "GFS", "GFS-kernel", "lvm2-cluster" ]:
          if self.cInfo["policy"].pkgByName(pkg) != None:
             return True

       # enable if any related file is present
       for fname in [ "/etc/cluster/cluster.conf", "/proc/cluster" ]:
          try:	 os.stat(fname)
          except:pass
          else:  return True

       # no data related to RHCS/GFS exists
       return False

    def has_gfs(self):
        fp = open("/proc/mounts","r")
        for line in fp.readlines():
           mntline = line.split(" ")
           if mntline[2] == "gfs":
              return True
        fp.close()
        return False

    def diagnose(self):
        try: rhelver = self.cInfo["policy"].pkgDictByName("redhat-release")[0]
        except: rhelver = None

        # FIXME: we should only run tests specific for the version, now just do them all regardless
        if rhelver == "4" or True:
           # check that kernel module packages are installed for
           # running kernel version
           pkgs_check = [ "dlm-kernel" , "cman-kernel" ]
           if self.has_gfs(): pkgs_check.append("GFS-kernel")

           for pkgname in pkgs_check:
               found = 0
               if self.cInfo["policy"].isKernelSMP() and self.cInfo["policy"].pkgByName(pkgname):
                   found = 1 # -one- means package found (but not for same version as kernel)
                   pkgname = pkgname + "-smp"

               for pkg in self.cInfo["policy"].allPkgsByName(pkgname):
                   found = 1
                   for reqline in self.cInfo["policy"].pkgRequires("%s-%s-%s" % (pkg[0],pkg[1],pkg[2]) ):
                       if reqline[0] == 'kernel-smp' and reqline[1] == '=':
                           reqline[2] = reqline[2] + "smp"

                       if ( (not self.cInfo["policy"].isKernelSMP() and reqline[0] == 'kernel') or (self.cInfo["policy"].isKernelSMP() and reqline[0] == 'kernel-smp') ) and reqline[1] == '=' and reqline[2] == self.cInfo["policy"].kernelVersion():
                           found = 2
                           break

               if found == 0:
                   self.addDiagnose("required package is missing: %s" % pkgname)
               elif found == 1:
                   self.addDiagnose("required package is not installed for current kernel: %s" % pkgname)

           # check if the minimum set of packages is installed
           # for RHEL4 RHCS(ccs, cman, cman-kernel, magma, magma-plugins, (dlm, dlm-kernel) || gulm, perl-Net-Telnet, rgmanager, fence)
           # RHEL4 GFS (GFS, GFS-kernel, ccs, lvm2-cluster, fence)

           for pkg in [ "ccs", "cman", "magma", "magma-plugins", "perl-Net-Telnet", "rgmanager", "fence" ]:
               if self.cInfo["policy"].pkgByName(pkg) == None:
                  self.addDiagnose("required package is missing: %s" % pkg)

           # (dlm, dlm-kernel) || gulm
           if not ((self.cInfo["policy"].pkgByName("dlm") and self.cInfo["policy"].pkgByName("dlm-kernel")) or self.cInfo["policy"].pkgByName("gulm")):
               self.addDiagnose("required packages are missing: (dlm, dlm-kernel) || gulm")

           # let's make modules are loaded
           mods_check = [ "cman", "dlm" ]
           if self.has_gfs(): mods_check.append("gfs")
           for module in mods_check:
               if len(self.fileGrep("^%s " % module, "/proc/modules")) == 0:
                   self.addDiagnose("required package is present but not loaded: %s" % module)

           # check if all the needed daemons are active at sosreport time
           # check if they are started at boot time in RHEL4 RHCS (cman, ccsd, rgmanager, fenced)
           # and GFS (gfs, ccsd, clvmd, fenced)
           checkserv = [ "cman", "ccsd", "rgmanager", "fenced" ]
           if self.has_gfs(): checkserv.extend( ["gfs", "clvmd"] )
           for service in checkserv:
               status, output = commands.getstatusoutput("/sbin/service %s status" % service)
               if status:
                   self.addDiagnose("service %s is not running" % service)
               else:
                   # service is running, extra sanity checks
                   if service == "fenced":
                       # also make sure fenced is a registered cluster service
                       try:
                           if len(self.fileGrep("^Fence Domain:\W", "/proc/cluster/services")) == 0:
                               self.addDiagnose("fencing service is not registered with cman")
                       except:
                           pass
                   elif service == "rgmanager":
                       # also make sure rgmanager is a registered cluster service
                       try:
                           if len(self.fileGrep("^User:\W*usrm::manager", "/proc/cluster/services")) == 0:
                               self.addDiagnose("rgmanager is not registered with cman")
                       except:
                           pass

               if not self.cInfo["policy"].runlevelDefault() in self.cInfo["policy"].runlevelByService(service):
                   self.addDiagnose("service %s is not started in default runlevel" % service)

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
               if status == 0 or self.cInfo["policy"].runlevelDefault() in self.cInfo["policy"].runlevelByService("acpid"):
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
        self.collectExtOutput("/usr/bin/cman_tool status")
        self.collectExtOutput("/usr/bin/cman_tool services")
        self.collectExtOutput("/usr/bin/cman_tool -af nodes")
        self.collectExtOutput("/usr/bin/ccs_tool lsnode")
        self.collectExtOutput("/usr/bin/openais-cfgtool -s")
        self.collectExtOutput("/usr/bin/clustat")

        self.collectExtOutput("/sbin/ipvsadm -L", root_symlink = "ipvsadm_-L")

        if self.isOptionEnabled('gfslockdump'): self.do_gfslockdump()
        if self.isOptionEnabled('lockdump'): self.do_lockdump()
        if self.isOptionEnabled('taskdump'): self.do_taskdump()

        return

    def do_taskdump(self):
        if not os.access("/proc/sysrq-trigger", os.W_OK):
            return

        commands.getstatusoutput("echo t > /proc/sysrq-trigger")
        time.sleep(5)
        commands.getstatusoutput("echo t > /proc/sysrq-trigger")
        time.sleep(5)
        commands.getstatusoutput("echo t > /proc/sysrq-trigger")

        self.addCopySpec("/var/log/messages")

    def do_lockdump(self):
        try:
            fp = open("/proc/cluster/services","r")
        except:
            return
        for line in fp.readlines():
           if line[0:14] == "DLM Lock Space":
              try:
                 lockspace = line.split('"')[1]
              except:
                 pass
              else:
                 commands.getstatusoutput("echo %s > /proc/cluster/dlm_locks" % lockspace)
                 self.collectOutputNow("cat /proc/cluster/dlm_locks", root_symlink = "dlm_locks_%s" % lockspace)
        fp.close()

    def get_locking_proto(self):
        # FIXME: what's the best way to find out ?
        return "lock_dlm"
        return "lock_gulm"

    def do_gfslockdump(self):
        fp = open("/proc/mounts","r")
        for line in fp.readlines():
           mntline = line.split(" ")
           if mntline[2] == "gfs":
              self.collectExtOutput("/sbin/gfs_tool lockdump %s" % mntline[1], root_symlink = "gfs_lockdump_" + self.mangleCommand(mntline[1]) )
        fp.close()

    def do_rgmgr_bt(self):
        # FIXME: threads backtrace
        return

    def postproc(self):
        self.doRegexSub("/etc/cluster/cluster.conf", r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")", r"\1***")
        return

    def is_cluster_quorate(self):
        # FIXME: use self.fileGrep() instead
        output = commands.getoutput("/bin/cat /proc/cluster/status | grep '^Membership state: '")
        try:
            if output[18:] == "Cluster-Member":
                return True
            else:
                return False
        except:
            pass
        return None

    def get_gfs_sb_field(self, device, field):
        for line in commands.getoutput("/sbin/gfs_tool sb %s all" % device).split("\n"):
            if re.match('^\W*%s = ' % field, line):
                return line.split("=")[1].strip()
        return False
