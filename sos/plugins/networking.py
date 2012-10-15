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
import os
import re

class networking(sos.plugintools.PluginBase):
    """network related information
    """
    optionList = [("traceroute", "collects a traceroute to rhn.redhat.com", "slow", False)]

    def get_bridge_name(self,brctlFile):
        """Return a dictionary for which key are bridge name according to the
        output of brctl show stored in brctlFile.
        """
        out=[]
        fp = open(brctlFile, 'r')
        for line in fp.readlines():
            if line.startswith("bridge name") or line.isspace() or line[:1].isspace():
                continue
            brName, brRest = line.split(None, 1)
            out.append(brName)
        fp.close()
        return out

    def get_interface_name(self,ipaddrFile):
        """Return a dictionary for which key are interface name according to the
        output of ifconifg-a stored in ifconfigFile.
        """
        out={}
        for interface in open(ipaddrFile, 'r').readlines():
            match=re.match(r'.*link/ether.*', interface)
            if match:
                int=match.string.split(':')[1].lstrip()
                out[int]=True
        return out

    def collectIPTable(self,tablename):
        """ When running the iptables command, it unfortunately auto-loads
        the modules before trying to get output.  Some people explicitly
        don't want this, so check if the modules are loaded before running
        the command.  If they aren't loaded, there can't possibly be any
        relevant rules in that table """

        cmd = "/sbin/iptables -t "+tablename+" -nvL"

        (status, output, time) = self.callExtProg("/sbin/lsmod | grep -q "+tablename)
        if status == 0:
            self.collectExtOutput(cmd)
        else:
            self.writeTextToCommand(cmd,"IPTables module "+tablename+" not loaded\n")

    def setup(self):
        self.addCopySpec("/proc/net/")
        self.addCopySpec("/etc/nsswitch.conf")
        self.addCopySpec("/etc/yp.conf")
        self.addCopySpec("/etc/inetd.conf")
        self.addCopySpec("/etc/xinetd.conf")
        self.addCopySpec("/etc/xinetd.d")
        self.addCopySpec("/etc/host*")
        self.addCopySpec("/etc/resolv.conf")
        self.collectExtOutput("/sbin/ifconfig -a", symlink = "ifconfig")
        ipaddrFile=self.collectOutputNow("/sbin/ip -o addr", symlink = "ip_addr")
        self.collectExtOutput("/sbin/route -n", symlink = "route")
        self.collectIPTable("filter")
        self.collectIPTable("nat")
        self.collectIPTable("mangle")
        self.collectExtOutput("/bin/netstat -s")
        self.collectExtOutput("/bin/netstat -agn")
        self.collectExtOutput("/bin/netstat -neopa", symlink = "netstat")
        self.collectExtOutput("/sbin/ip route show table all")
        self.collectExtOutput("/sbin/ip link")
        self.collectExtOutput("/sbin/ip address")
        self.collectExtOutput("/sbin/ifenslave -a")
        self.collectExtOutput("/sbin/ip mroute show")
        self.collectExtOutput("/sbin/ip maddr show")
        self.collectExtOutput("/sbin/ip neigh show")
        if ipaddrFile:
            for eth in self.get_interface_name(ipaddrFile):
                self.collectExtOutput("/sbin/ethtool "+eth)
                self.collectExtOutput("/sbin/ethtool -i "+eth)
                self.collectExtOutput("/sbin/ethtool -k "+eth)
                self.collectExtOutput("/sbin/ethtool -S "+eth)
                self.collectExtOutput("/sbin/ethtool -a "+eth)
                self.collectExtOutput("/sbin/ethtool -c "+eth)
                self.collectExtOutput("/sbin/ethtool -g "+eth)
        if self.getOption("traceroute"):
            self.collectExtOutput("/bin/traceroute -n rhn.redhat.com")
        if os.path.exists("/usr/sbin/brctl"):
            brctlFile=self.collectOutputNow("/usr/sbin/brctl show")
            if brctlFile:
                for brName in self.get_bridge_name(brctlFile):
                    self.collectExtOutput("/usr/sbin/brctl showstp "+brName)
        return

