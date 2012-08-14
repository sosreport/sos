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
import os
import re

class networking(Plugin, RedHatPlugin):
    """network related information
    """
    optionList = [("traceroute", "collects a traceroute to rhn.redhat.com", "slow", False)]

    def get_interface_name(self,ipaddrOut):
        """Return a dictionary for which key are interface name according to the
        output of ifconifg-a stored in ifconfigFile.
        """
        out={}
        for line in ipaddrOut[1].splitlines():
            match=re.match('.*link/ether', line)
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


        (status, output, time) = self.callExtProg("/sbin/lsmod | grep -q "+tablename)
        if status == 0:
            cmd = "/sbin/iptables -t "+tablename+" -nvL"
            self.collectExtOutput(cmd)

    def setup(self):
        self.addCopySpecs([
            "/proc/net",
            "/etc/nsswitch.conf",
            "/etc/yp.conf",
            "/etc/inetd.conf",
            "/etc/xinetd.conf",
            "/etc/xinetd.d",
            "/etc/host*",
            "/etc/resolv.conf"])
        ipaddrFile=self.collectOutputNow("/sbin/ip -o addr", root_symlink = "ip_addr")
        ipaddrOut=self.callExtProg("/sbin/ip -o addr")
        self.collectExtOutput("/sbin/route -n", root_symlink = "route")
        self.collectIPTable("filter")
        self.collectIPTable("nat")
        self.collectIPTable("mangle")
        self.collectExtOutput("/bin/netstat -s")
        self.collectExtOutput("/bin/netstat -agn")
        self.collectExtOutput("/bin/netstat -neopa", root_symlink = "netstat")
        self.collectExtOutput("/sbin/ip route show table all")
        self.collectExtOutput("/sbin/ip -6 route show table all")
        self.collectExtOutput("/sbin/ip link")
        self.collectExtOutput("/sbin/ip address")
        self.collectExtOutput("/sbin/ifenslave -a")
        self.collectExtOutput("/sbin/ip mroute show")
        self.collectExtOutput("/sbin/ip maddr show")
        if ipaddrOut:
            for eth in self.get_interface_name(ipaddrOut):
                self.collectExtOutput("/sbin/ethtool "+eth)
                self.collectExtOutput("/sbin/ethtool -i "+eth)
                self.collectExtOutput("/sbin/ethtool -k "+eth)
                self.collectExtOutput("/sbin/ethtool -S "+eth)
                self.collectExtOutput("/sbin/ethtool -a "+eth)
                self.collectExtOutput("/sbin/ethtool -c "+eth)
                self.collectExtOutput("/sbin/ethtool -g "+eth)
        if self.getOption("traceroute"):
            self.collectExtOutput("/bin/traceroute -n rhn.redhat.com")
