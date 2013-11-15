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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os
import re

class Networking(Plugin):
    """network related information
    """
    plugin_name = "networking"
    trace_host = "www.example.com"
    option_list = [("traceroute", "collects a traceroute to %s" % trace_host,
                        "slow", False)]
    
    def setup(self):
        super(Networking, self).setup()

    def get_bridge_name(self,brctl_out):
        """Return a list for which items are bridge name according to the
        output of brctl show stored in brctl_file.
        """
        out=[]
        for line in brctl_out[1].splitlines():
            if line.startswith("bridge name") \
               or line.isspace() \
               or line[:1].isspace():
                continue
            br_name, br_rest = line.split(None, 1)
            out.append(br_name)
        return out

    def get_eth_interfaces(self,ip_link_out):
        """Return a dictionary for which keys are ethernet interface
        names taken from the output of "ip -o link".
        """
        out={}
        for line in ip_link_out[1].splitlines():
            match=re.match('.*link/ether', line)
            if match:
                iface=match.string.split(':')[1].lstrip()
                out[iface]=True
        return out

    def collect_iptable(self,tablename):
        """ When running the iptables command, it unfortunately auto-loads
        the modules before trying to get output.  Some people explicitly
        don't want this, so check if the modules are loaded before running
        the command.  If they aren't loaded, there can't possibly be any
        relevant rules in that table """


        (status, output, time) = self.call_ext_prog("lsmod | grep -q "+tablename)
        if status == 0:
            cmd = "iptables -t "+tablename+" -nvL"
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
            "/etc/resolv.conf"
            "/etc/network*",
            "/etc/NetworkManager/NetworkManager.conf",
            "/etc/NetworkManager/system-connections",
            "/etc/dnsmasq*"])
        self.add_forbidden_path("/proc/net/rpc/use-gss-proxy")
        self.add_forbidden_path("/proc/net/rpc/*/channel")
        self.add_forbidden_path("/proc/net/rpc/*/flush")

        ip_addr_file=self.get_cmd_output_now("ip -o addr", root_symlink = "ip_addr")
        self.add_cmd_output("route -n", root_symlink = "route")
        self.collect_iptable("filter")
        self.collect_iptable("nat")
        self.collect_iptable("mangle")
        self.add_cmd_output("netstat -s")
        self.add_cmd_output("netstat -agn")
        self.add_cmd_output("netstat -neopa", root_symlink = "netstat")
        self.add_cmd_output("ip route show table all")
        self.add_cmd_output("ip -6 route show table all")
        self.add_cmd_output("ip link")
        self.add_cmd_output("ip address")
        self.add_cmd_output("ifenslave -a")
        self.add_cmd_output("ip mroute show")
        self.add_cmd_output("ip maddr show")
        self.add_cmd_output("ip neigh show")
        ip_link_out=self.call_ext_prog("ip -o link")
        if ip_link_out:
            for eth in self.get_eth_interfaces(ip_link_out):
                self.add_cmd_output("ethtool "+eth)
                self.add_cmd_output("ethtool -i "+eth)
                self.add_cmd_output("ethtool -k "+eth)
                self.add_cmd_output("ethtool -S "+eth)
                self.add_cmd_output("ethtool -a "+eth)
                self.add_cmd_output("ethtool -c "+eth)
                self.add_cmd_output("ethtool -g "+eth)

        brctl_file=self.add_cmd_output("brctl show")
        brctl_out=self.call_ext_prog("brctl show")
        if brctl_out:
            for br_name in self.get_bridge_name(brctl_out):
                self.add_cmd_output("brctl showstp "+br_name)

        if self.get_option("traceroute"):
            self.add_cmd_output("/bin/traceroute -n %s" % self.trace_host)

        return

    def postproc(self):
        for root, dirs, files in os.walk("/etc/NetworkManager/system-connections"):
            for net_conf in files:
                self.do_file_sub("/etc/NetworkManager/system-connections/"+net_conf, r"psk=(.*)",r"psk=***")

class RedHatNetworking(Networking, RedHatPlugin):
    """network related information for RedHat based distribution
    """
    trace_host = "rhn.redhat.com"
    def setup(self):
        super(RedHatNetworking, self).setup()

class UbuntuNetworking(Networking, UbuntuPlugin):
    """network related information for Ubuntu based distribution
    """
    trace_host = "archive.ubuntu.com"

    def setup(self):
        super(UbuntuNetworking, self).setup()

        self.add_copy_specs([
            "/etc/resolvconf",
            "/etc/ufw",
            "/var/log/ufw.Log",
            "/etc/resolv.conf"])
        self.add_cmd_output("/usr/sbin/ufw status")
        self.add_cmd_output("/usr/sbin/ufw app list")
        if self.get_option("traceroute"):
            self.add_cmd_output("/usr/sbin/traceroute -n %s" % self.trace_host)

