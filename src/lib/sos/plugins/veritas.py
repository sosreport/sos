### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import commands
import sos.plugintools

class veritas(sos.plugintools.PluginBase):
    """veritas related information
    """
    # License
    license = {"VXLICENSE" : "/usr/sbin/vxlicense", "VXLICREP" : "/usr/sbin/vxlicense",
               "OLD_VXLICREP" : "/var/adm/VRTSshrd/VRTSlic/bin/vxlicrep",
               "VXLICTEST" : "/sbin/vxlictest"}
    
    # Slim
    slim = {"VSSAT" : "/opt/VRTSat/bin/vssat"}
    
    # VxVM
    vxvm = {"VXDCTL" : "/usr/sbin/vxdctl", "VXPRINT" : "/usr/lib/vxvm/diag.d/vxkprint",
            "VXDISK" : "/usr/sbin/vxdisk", "VXDG" : "/usr/sbin/vxdg", "VXRLINK" : "/usr/sbin/vxrlink",
            "MACROSD" : "/usr/lib/vxvm/diag.d/macros.d", "VXDMPADM" : "/usr/sbin/vxdmpadm",
            "VXSTAT" : "/usr/sbin/vxstat", "VXCONFIGD" : "/usr/sbin/vxconfigd",
            "VXDDLADM" : "/usr/sbin/vxddladm", "VXDIAGDIR" : "/usr/lib/vxvm/diag.d",
            "VXTRACE" : "/usr/sbin/vxtrace", "VXRVG" : "/usr/sbin/vxrvg",
            "VXCLUSTADM" : "/etc/vx/bin/vxclustadm", "VXVSET" : "/usr/sbin/vxvset"}
    
    # VFR
    vfr = {"VFRC" : "/usr/sbin/vfrc"}
    
    # VxFS
    vxfs = {"VXLD_PRINT" : "/sbin/vxld_print", "FSCKPTADM" : "/usr/lib/fs/vxfs/fsckptadm",
            "FCLADM" : "/opt/VRTS/bin/fcladm", "FSAPADM" : "/opt/VRTS/bin/fsapadm",
            "FSDB" : "/opt/VRTS/bin/fsdb", "FSADM" : "/usr/lib/fs/vxfs/fsadm",
            "VXTUNEFS" : "/usr/lib/fs/vxfs/vxtunefs", "FSTYP" : "/usr/lib/fs/vxfs/fstyp"}
    
    #vcs
    vcs = {"HARES" : "/opt/VRTSvcs/bin/hares","HAGRP" : "/opt/VRTSvcs/bin/hagrp",
           "HASYS" : "/opt/VRTSvcs/bin/hasys","HACLUS" : "/opt/VRTSvcs/bin/haclus",
           "HACONF" : "/opt/VRTSvcs/bin/haconf","HASTATUS" : "/opt/VRTSvcs/bin/hastatus",
           "GABCONFIG" : "/sbin/gabconfig", "GABDISK" : "/sbin/gabdisk",
           "HATYPE" : "/opt/VRTSvcs/bin/hatype", "LLTSTAT" : "/sbin/lltstat",
           "GABDEBUG" : "/sbin/gabdebug", "GABDISKHB" : "/sbin/gabdiskhb",
           "GABDISKX" : "/sbin/gabdiskx", "GABPORT" : "/sbin/gabport",
           "HAD" : "/opt/VRTSvcs/bin/had","GETCOMMS" : "/opt/VRTSgab/getcomms",
           "HADISCOVER" : "/opt/VRTSvcs/bin/hadiscover",
           "OraDiscovery" : "/opt/VRTSvcs/bin/Oracle/OraDiscovery.pl",
           "GETVCSOPS" : "/opt/VRTSvcs/bin/getvcsops","GETDBAC" : "/opt/VRTSvcs/bin/getdbac"}
    # module list
    module_list = ["vxvm", "vxfs", "isis", "samba", "vcs", "spnas", "txpt", "vsap",
                   "vrtsisp", "vlic", "vrw", "cpi", "cca", "spc", "vxfen", "cmc",
                   "slim", "sfms", "dbed","vxportal","vxspec","vxio","vxdmpfs",
                   "vxdmp"]
    
    package_list = ["VRTSfppm","VRTSfspro","VRTSob","VRTSlvmconv","VRTSvxmsa",
                    "VRTSfsdoc", "VRTSap","VRTSap","VRTScpi","VRTSvxvm","VRTSvmpro",
                    "VRTSddlpr","VRTSobgui","VRTSvmman","VRTScccfg","VRTSsal",
                    "VRTSccshd","VRTStep","VRTStep","VRTSvxfs","VRTSalloc",
                    "VRTSfsman","VRTSClariionCx600","VRTSccdam","VRTSccsta",
                    "VRTSvlic"]
    
    def checkenabled(self):
        for pkgname in self.package_list:
            if self.cInfo["policy"].allPkgsByName(pkgname):
                return True
        return False
    
    def get_vxfs(self):
        """ capture information related to VXFS 
        """
        self.addCopySpec("/etc/vx/tunefstab")
        # get all vxfs mountpoints and capture various information
        for mntpnt in commands.getoutput("/bin/df -P -T | /bin/grep vxfs | /usr/bin/awk '{ print $7 }'"):
            bdev = commands.getoutput("/bin/mount | /bin/grep 'on %s' | /usr/bin/awk '{ print $1 }'" % mntpnt)
            if mntpnt == "/":
                mntname="_root_"
            else:
                mntname=commands.getoutput("/bin/echo %s | sed s#/#_#g" % mntpnt)
            self.collectExtOutput("/bin/df -k %s" % mntpnt)
            self.collectExtOutput("%s -v %s" % (self.vxfs["FSTYP"],bdev))
            self.collectExtOutput("%s %s" % (self.vxfs["FSADM"],mntpnt))
            self.collectExtOutput("%s -p %s" % (self.vxfs["VXTUNEFS"],mntpnt))
            self.collectExtOutput("%s state %s" % (self.vxfs["FCLADM"],mntpnt))
            self.collectExtOutput("%s queryfs %S" % (self.vxfs["FSAPADM"],mntpnt))
            self.collectExtOutput("%s -n 'VERITAS File System' -l" % self.license["VXLICTEST"])
        return
    
    def get_vxvm(self):
        """ Veritas volume manager information 
        """
        # vxdctl and vxclustadm information
        self.collectExtOutput("%s mode" % self.vxvm["VXDCTL"])
        self.collectExtOutput("%s -c mode" % self.vxvm["VXDCTL"])
        self.collectExtOutput("%s license" % self.vxvm["VXDCTL"])
        self.collectExtOutput("%s support" % self.vxvm["VXDCTL"])
        nodestate=commands.getoutput("%s help | grep '\[-v\] nodestate" % self.vxvm["VXCLUSTADM"])
        if nodestate is None:
            self.collectExtOutput("%s -v nodestate" % self.vxvm["VXCLUSTADM"])
        else:
            self.collectExtOutput("%s nodestate" % self.vxvm["VXCLUSTADM"])
        nidmap=commands.getoutput("% help | grep 'nidmap'" % self.vxvm["VXCLUSTADM"])
        if nidmap is None:
            self.collectExtOutput("%s nidmap" % self.vxvm["VXCLUSTADM"])
            self.collectExtOutput("%s dumpmsg" % self.vxvm["VXCLUSTADM"])
            self.collectExtOutput("%s transstate" % self.vxvm["VXCLUSTADM"])
        self.addCopySpec("/var/adm/vx/cmdlog*")
        self.addCopySpec("/var/adm/vx/translog*")
        self.addCopySpec("/VXVM*UPGRADE*")
        self.addCopySpec("/var/vxvm")
        self.collectExtOutput("/bin/ls -l /dev/vx*")
        self.collectExtOutput("/bin/ls -laR /etc/vx")
        self.addCopySpec("/etc/vx")
        self.addCopySpec("/etc/vxvmconf")
        self.addCopySpec("/etc/default/vxassist")
        # vxvm - vxdctl information
        vxdctlmode=commands.getoutput("%s mode | /usr/bin/awk ' { print $2 } '" % self.vxvm["VXDCTL"])
        if vxdctlmode == "disabled" or vxdctlmode == "not-running":
            return
        # vxvm - vxdisk information
        self.collectExtOutput("%s list" % self.vxvm["VXDISK"])
        vxdisk_path=commands.getoutput("%s help | grep 'path'" % self.vxvm["VXDISK"])
        if vxdisk_path is None:
            self.collectExtOutput("%s path" % self.vxvm["VXDISK"])
        self.collectExtOutput("%s -o alldgs list" % self.vxvm["VXDISK"])
        self.collectExtOutput("%s -s list" % self.vxvm["VXDISK"])
        for i in commands.getoutput("%s -q list | /usr/bin/awk ' { print $1 } ' | /bin/grep -v '^-$'" % self.vxvm["VXDISK"]):
            self.collectExtOutput("%s list %s" % (self.vxvm["VXDISK"], i))
        # vxvm - vxdg information
        self.collectExtOutput("%s list" % self.vxvm["VXDG"])
        self.collectExtOutput("%s free" % self.vxvm["VXDG"])
        if commands.getoutput("%s help | grep 'bootdg'" % self.vxvm["VXDG"]) is None:
            self.collectExtOutput("%s bootdg" % self.vxvm["VXDG"])
        # vxvm - vxtrace information
        self.collectExtOutput("%s -lE" % self.vxvm["VXTRACE"])
        for i in commands.getoutput("%s -q list | /usr/bin/awk ' { print $1 } '" % self.vxvm["VXDG"]):
            self.collectExtOutput("%s list %i" % (self.vxvm["VXDG"],i))
            self.collectExtOutput("%s -g %s" % (self.vxvm["VXSTAT"],i))
            self.collectExtOutput("%s -mvpshr -g %s" % (self.vxvm["VXPRINT"],i))
            self.collectExtOutput("%s -m -g %s" % (self.vxvm["VXPRINT"],i))
        self.collectExtOutput("%s list" % self.vxvm["VXVSET"])
        self.addCopySpec("/proc/sys/vxvm/vxinfo")
        self.addcopyspec("/proc/sys/vxvm/vxio")
        # vvr/svrm specific information
        self.addCopySpec("/etc/vx/vras")
        return
    
    def get_vcs(self):
        """ Veritas cluster information
        """
        self.collectExtOutput("%s -dump" % self.vcs["HACONF"])
        self.addCopySpec("/etc/VRTSvcs/*")
        self.addCopySpec("/etc/llt*")
        self.addCopySpec("/etc/gab*")
        
        #copy log files, etc
        self.addCopySpec("/var/VRTSvcs/*")
        self.addCopySpec("/var/adm/streams")
        self.addCopySpec("/var/adm/VRTSshrd/VRTSlic")
        
        # get state information
        
        self.collectExtOutput(self.vcs[LLTSTAT])
        self.collectExtOutput("%s -vvn" % self.vcs["LLTSTAT"])
        self.collectExtOutput("%s -a" % self.vcs["GABCONFIG"])
        self.collectExtOutput("%s -l" % self.vcs["GABDISK"])
        self.collectExtOutput("%s -l" % self.vcs["GABDISKHB"])
        self.collectExtOutput("%s -l" % self.vcs["GABDISKX"])
        
        self.collectExtOutput("%s -summary" % self.vcs["HASTATUS"])
        self.collectExtOutput("%s -display -all" % self.vcs["HARES"])
        self.collectExtOutput("%s -dep" % self.vcs["HARES"])
        self.collectExtOutput("%s -display -all" % self.vcs["HAGRP"])
        self.collectExtOutput("%s -dep" % self.vcs["HAGRP"])
        self.collectExtOutput("%s -display" % self.vcs["HATYPE"])
        self.collectExtOutput("%s -display" % self.vcs["HASYS"])
        self.collectExtOutput("%s -display" % self.vcs["HACLUS"])
        
        # TODO: get agents section
        
        # get cores
        self.addCopySpec("/opt/VRTSvcs/bin/core*")
        self.addCopySpec("/opt/VRTSvcs/core*")
        
        # TODO: get comms
        
        # vcs gui
        self.addCopySpec("/opt/VRTSvcs/gui/conf")
        
        # vcs quickstart
        vcsmode = commands.getoutput("%s -value VCSMODE" % self.vcs["HACLUS"])
        if vcsmode == "VCSQS":
            self.collectExtOutput("%s -discover Application User" % self.vcs["HADISCOVER"])
            self.collectExtOutput("%s -discover Mount MountPoint" % self.vcs["HADISCOVER"])
            self.collectExtOutput("%s -discover NFS Nservers" % self.vcs["HADISCOVER"])
            self.collectExtOutput("%s -discover NIC Device" % self.vcs["HADISCOVER"])
            self.collectExtOutput("%s -discover Oracle Instances" % self.vcs["HADISCOVER"])
            self.collectExtOutput("%s -discover Share PathName" % self.vcs["HADISCOVER"])
    
    def get_vxfen(self):
        pass
    
    def setup(self):
        # TODO: Do necessary checks for different archs, i.e. z-series and ia64
        self.collectExtOutput("/bin/rpm -qa | /bin/grep -i VRTS | /bin/grep -v doc | /bin/grep -v man")
        # Determine what information to collect based on installed packages
        if self.cInfo["policy"].pkgByName("VRTSvxfs"): get_vxfs()
        if self.cInfo["policy"].pkgByName("VRTSvxfs"): get_vxvm()
        # I think if one of these is present it is assumed that VCS is installed
        if self.cInfo["policy"].pkgByName("VRTSvmpro") or self.cInfo["policy"].pkgByName("VRTSfspro"): get_vcs()
        return

