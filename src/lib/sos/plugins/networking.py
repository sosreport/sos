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
    
    
    def collect(self):
        self.copyFileOrDir("/etc/nsswitch.conf")
        self.copyFileOrDir("/etc/yp.conf")
        self.copyFileOrDir("/etc/inetd.conf")
        self.copyFileOrDir("/etc/xinetd.conf")
        self.copyFileOrDir("/etc/xinetd.d")
        self.copyFileGlob("/etc/host*")
        self.copyFileOrDir("/etc/resolv.conf")
        # self.copyFileOrDir("/etc/sysconfig/iptables-config")
        # The above is redundant
        ifconfigFile=self.runExe("/sbin/ifconfig -a")
        self.runExe("/sbin/route -n")
        self.runExe("/sbin/ipchains -nvL")
        self.runExe("/sbin/iptables -t filter -nvL")
        self.runExe("/sbin/iptables -t nat -nvL")
        self.runExe("/sbin/iptables -t mangle -nvL")
        if ifconfigFile:
            for eth in self.get_interface_name(ifconfigFile):
                self.runExe("/sbin/ethtool "+eth)
            
        return

