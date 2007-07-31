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
import os,re,commands

class networking(sos.plugintools.PluginBase):
    """network related information
    """
    optionList = [("traceroute", "collects a traceroute to rhn.redhat.com", "slow", False)]

    def get_interface_name(self,ifconfigFile):
        """Return a dictionary for which key are interface name according to the
        output of ifconifg-a stored in ifconfigFile.
        """
        out={}
        if(os.path.isfile(ifconfigFile)):
            f=open(ifconfigFile,'r')
            content=f.read()
            f.close()
            reg=re.compile(r"^(eth\d+)\D",re.MULTILINE)
            for name in reg.findall(content):
                out[name]=1
        return out

    def collectIPTable(self,tablename):
        """ When running the iptables command, it unfortunately auto-loads
        the modules before trying to get output.  Some people explicitly
        don't want this, so check if the modules are loaded before running
        the command.  If they aren't loaded, there can't possibly be any
        relevant rules in that table """

        cmd = "/sbin/iptables -t "+tablename+" -nvL"

        (status, output) = commands.getstatusoutput("/sbin/lsmod | grep -q "+tablename)
        if status == 0:
            self.collectExtOutput(cmd)
        else:
            self.writeTextToCommand(cmd,"IPTables module "+tablename+" not loaded\n")

    def setup(self):
        self.addCopySpec("/etc/nsswitch.conf")
        self.addCopySpec("/etc/yp.conf")
        self.addCopySpec("/etc/inetd.conf")
        self.addCopySpec("/etc/xinetd.conf")
        self.addCopySpec("/etc/xinetd.d")
        self.addCopySpec("/etc/host*")
        self.addCopySpec("/etc/resolv.conf")
        ifconfigFile=self.collectOutputNow("/sbin/ifconfig -a", root_symlink = "ifconfig")
        self.collectExtOutput("/sbin/route -n", root_symlink = "route")
        self.collectExtOutput("/sbin/ipchains -nvL")
        self.collectIPTable("filter")
        self.collectIPTable("nat")
        self.collectIPTable("mangle")
        self.collectExtOutput("/bin/netstat -nap")
        if ifconfigFile:
            for eth in self.get_interface_name(ifconfigFile):
                self.collectExtOutput("/sbin/ethtool "+eth)
        if self.isOptionEnabled("traceroute"):
            # The semicolon prevents the browser from thinking this is a link when viewing the report
            self.collectExtOutput("/bin/traceroute  rhn.redhat.com;")
            
        return

