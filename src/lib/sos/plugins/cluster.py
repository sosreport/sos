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
import commands

class cluster(sos.plugintools.PluginBase):
    """cluster suite and GFS related information
    """
    def diagnose(self):
        rhelver = self.cInfo["policy"].pkgDictByName("fedora-release")[0]
        if rhelver == "6":
           # check if the minimum set of packages is installed
           # for RHEL4 RHCS(ccs, cman, cman-kernel, magma, magma-plugins, (dlm, dlm-kernel) || gulm, perl-Net-Telnet, rgmanager, fence)
           # RHEL4 GFS (GFS, GFS-kernel, ccs, lvm2-cluster, fence)
           for pkg in [ "ccs", "cman", "cman-kernel", "magma", "magma-plugins", "perl-Net-Telnet", "rgmanager", "fence" ]:
              if self.cInfo["policy"].pkgByName(pkg) == None:
                 self.addDiagnose("required package is missing: %s" % pkg)

           # check if all the needed daemons are active at sosreport time
           # check if they are started at boot time in RHEL4 RHCS (cman, ccsd, rgmanager, fenced)
           # and GFS (gfs, ccsd, clvmd, fenced)
           for service in [ "cman", "ccsd", "rgmanager", "fence" ]:
              if commands.getstatus("/sbin/service %s status" % service):
                 self.addDiagnose("service %s is not running" % service)

              if not self.cInfo["policy"].runlevelDefault() in self.cInfo["policy"].runlevelByService(service):
                 self.addDiagnose("service %s is not started in default runlevel" % service)

           # FIXME: what locking are we using ? check if packages exist
#           if self.cInfo["policy"].pkgByName(pkg) and self.cInfo["policy"].pkgByName(pkg) and not self.cInfo["policy"].pkgByName(pkg)

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
        return

    def postproc(self):
        self.doRegexSub("/etc/cluster/cluster.conf", r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")", r"\1***")
        return
