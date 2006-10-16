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
import os,re

class networking(sos.plugintools.PluginBase):
    """This plugin gathers network related information
    """

    def get_interface_name(self,ifconfigFile):
        """Return a dictionnary for wich key are intefrace name according to the
        output of ifcongif-a stored in ifconfigFile.
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
    
    
    def setup(self):
        self.addCopySpec("/etc/nsswitch.conf")
        self.addCopySpec("/etc/yp.conf")
        self.addCopySpec("/etc/inetd.conf")
        self.addCopySpec("/etc/xinetd.conf")
        self.addCopySpec("/etc/xinetd.d")
        self.addCopySpec("/etc/host*")
        self.addCopySpec("/etc/resolv.conf")
        # self.addCopySpec("/etc/sysconfig/iptables-config")
        # The above is redundant
        ifconfigFile=self.collectExtOutput("/sbin/ifconfig -a")
        self.collectExtOutput("/sbin/route -n")
        self.collectExtOutput("/sbin/ipchains -nvL")
        self.collectExtOutput("/sbin/iptables -t filter -nvL")
        self.collectExtOutput("/sbin/iptables -t nat -nvL")
        self.collectExtOutput("/sbin/iptables -t mangle -nvL")
        self.collectExtOutput("/bin/netstat -nap")
        if ifconfigFile:
            for eth in self.get_interface_name(ifconfigFile):
                self.collectExtOutput("/sbin/ethtool "+eth)
            
        return

