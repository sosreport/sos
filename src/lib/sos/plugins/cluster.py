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
import commands, os
import time, libxml2

class cluster(sos.plugintools.PluginBase):
    """cluster suite and GFS related information
    """

    optionList = [("gfslockdump", 'gather output of gfs lockdumps', 'slow', False),
                  ('lockdump', 'gather dlm lockdumps', 'slow', False),
                  ('taskdump', 'trigger 3 SysRq+t dumps every 5 seconds', 'slow', False)]

    def checkenabled(self):
       # enable if any related package is installed
       for pkg in [ "ccs", "cman", "cman-kernel", "magma", "magma-plugins", 
		    "rgmanager", "fence", "dlm", "dlm-kernel", "gulm",
		    "GFS", "GFS-kernel", "lvm2-cluster" ]:
          if self.cInfo["policy"].pkgByName(pkg) != None:
             return True

       # enable if any related file is present
       for fname in [ "/etc/cluster/cluster.conf" ]:
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

           # check if all the needed daemons are active at sosreport time
           # check if they are started at boot time in RHEL4 RHCS (cman, ccsd, rgmanager, fenced)
           # and GFS (gfs, ccsd, clvmd, fenced)
           checkserv = [ "cman", "ccsd", "rgmanager", "fenced" ]
           if self.has_gfs(): checkserv.extend( ["gfs", "clvmd"] )
           for service in checkserv:
               status, output = commands.getstatusoutput("/sbin/service %s status" % service)
               if status:
                   self.addDiagnose("service %s is not running" % service)

               if not self.cInfo["policy"].runlevelDefault() in self.cInfo["policy"].runlevelByService(service):
                   self.addDiagnose("service %s is not started in default runlevel" % service)

           # is cluster quorate
           if not self.is_cluster_quorate():
               self.addDiagnose("cluster node is not quorate")

           # if there is no cluster.conf, diagnose() finishes here.
           try:    os.stat("/etc/cluster/cluster.conf")
           except: return

           # setup XML xpath context
           xml = libxml2.parseFile("/etc/cluster/cluster.conf")
           xpathContext = xml.xpathNewContext()

           # check fencing (warn on empty or manual)
           if len(xpathContext.xpathEval("/cluster/clusternodes/clusternode[not(fence/method/device)]")):
               self.addDiagnose("one or more nodes have no fencing agent configured")

           if len(xpathContext.xpathEval("/cluster/clusternodes/clusternode[/cluster/fencedevices/fencedevice[@agent='fence_manual']/@name=fence/method/device/@name]")):
               self.addDiagnose("one or more nodes have manual fencing agent configured (data integrity is not guaranteed)")

           # check for fs exported via nfs without nfsid attribute
           if len(xpathContext.xpathEval("/cluster/rm/service//fs[not(@fsid)]/nfsexport")):
               self.addDiagnose("one or more nfs file-system doesn't have a fsid attribute set.")

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

           fp = open("/etc/fstab","r")
           for fs in fp.readline().split():
#               fs = fs.split()
               if not fs or fs[0] == "#" or len(fs) < 6 or fs[2]!="gfs": continue
               lockproto = get_gfs_sb_field(fs[1], "sb_lockproto")
               if lockproto != "lock_" + get_locking_proto:
                   self.addDiagnose("gfs mountpoint (%s) is using the wrong locking protocol (%s)" % (fs[0], lockproto) )

               locktable = get_gfs_sb_field(fs[1], "sb_locktable")
               if not locktable: continue
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

        if self.isOptionEnabled('gfslockdump'): self.do_gfslockdump()
        if self.isOptionEnabled('lockdump'): self.do_lockdump()
        if self.isOptionEnabled('taskdump'): self.do_taskdump()

        return

    def do_taskdump(self):
        commands.getstatusoutput("echo t > /proc/sysrq-trigger")
        time.sleep(3)
        commands.getstatusoutput("echo t > /proc/sysrq-trigger")
        time.sleep(3)
        commands.getstatusoutput("echo t > /proc/sysrq-trigger")
        self.addCopySpec("/var/log/messages")

    def do_lockdump(self):
        fp = open("/proc/cluster/services","r")
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
        return "dlm"
        return "gulm"

    def do_gfslockdump(self):
        fp = open("/proc/mounts","r")
        for line in fp.readlines():
           mntline = line.split(" ")
           if mntline[2] == "gfs":
              self.collectExtOutput("/sbin/gfs_tool lockdump %s" % mntline[1])
        fp.close()

    def postproc(self):
        self.doRegexSub("/etc/cluster/cluster.conf", r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")", r"\1***")
        return

    def is_cluster_quorate(self):
        output = commands.getoutput("/bin/cat /proc/cluster/status | grep '^Membership state: '")
        try:
            if output[18:] == "Cluster-Member":
                return True
            else:
                return False
        except:
            pass
        return None

    def get_gfs_sb_field(self, mntpoint, field):
        for line in commands.getoutput("/sbin/gfs_tool sb %s all" % fs[1]):
            tostrip = "  " + field + " = "
            if line.startwith(tostrip):
                return line[len(tostrip):]
        return None

    def xpath_query_count(self, fname, query):
        return len(self.xpath_query(fname, query))

    def xpath_query(self, fname, query):
        xml = libxml2.parseFile(fname)
        xpathContext = xml.xpathNewContext()
        return xpathContext.xpathEval(query)

        # FIXME: use python libxml internals
        tmpout = commands.getoutput("/bin/echo xpath %s | /usr/bin/xmllint --shell /etc/cluster/cluster.conf")
        for tmpline in tmpout:
            if tmpline.startswith("Set contains "):
                tmpvalue = tmpline[14:].split(" ")[0]
                if tmpvalue == "NULL": return 0
                try: tmpvalue = int(tmpvalue)
                except: return False
                return tmpvalue
        return False




