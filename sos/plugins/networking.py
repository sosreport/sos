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

    def get_bridge_name(self,brctlOut):
        """Return a list for which items are bridge name according to the
        output of brctl show stored in brctlFile.
        """
        out=[]
        for line in brctlOut[1].splitlines():
            if line.startswith("bridge name") \
		or line.isspace() \
		or line[:1].isspace():
                continue
            brName, brRest = line.split(None, 1)
            out.append(brName)
        return out

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


        (status, output, time) = self.call_ext_prog("/sbin/lsmod | grep -q "+tablename)
        if status == 0:
            cmd = "/sbin/iptables -t "+tablename+" -nvL"
            self.add_cmd_output(cmd)

    def setup(self):
        self.add_copy_specs([
            "/proc/net/",
            "/etc/nsswitch.conf",
            "/etc/yp.conf",
            "/etc/inetd.conf",
            "/etc/xinetd.conf",
            "/etc/xinetd.d",
            "/etc/host*",
            "/etc/resolv.conf"])
        ipaddrFile=self.get_cmd_output_now("/sbin/ip -o addr", root_symlink = "ip_addr")
        ipaddrOut=self.call_ext_prog("/sbin/ip -o addr")
        self.add_cmd_output("/sbin/route -n", root_symlink = "route")
        self.collectIPTable("filter")
        self.collectIPTable("nat")
        self.collectIPTable("mangle")
        self.add_cmd_output("/bin/netstat -s")
        self.add_cmd_output("/bin/netstat -agn")
        self.add_cmd_output("/bin/netstat -neopa", root_symlink = "netstat")
        self.add_cmd_output("/sbin/ip route show table all")
        self.add_cmd_output("/sbin/ip -6 route show table all")
        self.add_cmd_output("/sbin/ip link")
        self.add_cmd_output("/sbin/ip address")
        self.add_cmd_output("/sbin/ifenslave -a")
        self.add_cmd_output("/sbin/ip mroute show")
        self.add_cmd_output("/sbin/ip maddr show")
        self.add_cmd_output("/sbin/ip neigh show")
        if ipaddrOut:
            for eth in self.get_interface_name(ipaddrOut):
                self.add_cmd_output("/sbin/ethtool "+eth)
                self.add_cmd_output("/sbin/ethtool -i "+eth)
                self.add_cmd_output("/sbin/ethtool -k "+eth)
                self.add_cmd_output("/sbin/ethtool -S "+eth)
                self.add_cmd_output("/sbin/ethtool -a "+eth)
                self.add_cmd_output("/sbin/ethtool -c "+eth)
                self.add_cmd_output("/sbin/ethtool -g "+eth)
        if self.get_option("traceroute"):
            self.add_cmd_output("/bin/traceroute -n rhn.redhat.com")

        if os.path.exists("/usr/sbin/brctl"):
            brctlFile=self.add_cmd_output("/usr/sbin/brctl show")
            brctlOut=self.call_ext_prog("/usr/sbin/brctl show")
            if brctlOut:
                for brName in self.get_bridge_name(brctlOut):
                    self.add_cmd_output("/usr/sbin/brctl showstp "+brName)
        return

