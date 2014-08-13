# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin
import os
import re


class Networking(Plugin):
    """network related information
    """
    plugin_name = "networking"
    trace_host = "www.example.com"
    option_list = [("traceroute", "collects a traceroute to %s" % trace_host,
                    "slow", False)]

    def get_bridge_name(self, brctl_file):
        """Return a list for which items are bridge name according to the
        output of brctl show stored in brctl_file.
        """
        out = []
        try:
            brctl_out = open(brctl_file).read()
        except:
            return out
        for line in brctl_out.splitlines():
            if line.startswith("bridge name") \
               or line.isspace() \
               or line[:1].isspace():
                continue
            br_name, br_rest = line.split(None, 1)
            out.append(br_name)
        return out

    def get_eth_interfaces(self, ip_link_out):
        """Return a dictionary for which keys are ethernet interface
        names taken from the output of "ip -o link".
        """
        out = {}
        for line in ip_link_out.splitlines():
            match = re.match('.*link/ether', line)
            if match:
                iface = match.string.split(':')[1].lstrip()
                out[iface] = True
        return out

    def collect_iptable(self, tablename):
        """ When running the iptables command, it unfortunately auto-loads
        the modules before trying to get output.  Some people explicitly
        don't want this, so check if the modules are loaded before running
        the command.  If they aren't loaded, there can't possibly be any
        relevant rules in that table """

        if self.check_ext_prog("grep -q %s /proc/modules" % tablename):
            cmd = "iptables -t "+tablename+" -nvL"
            self.add_cmd_output(cmd)

    def setup(self):
        super(Networking, self).setup()
        self.add_copy_specs([
            "/proc/net/",
            "/etc/nsswitch.conf",
            "/etc/yp.conf",
            "/etc/inetd.conf",
            "/etc/xinetd.conf",
            "/etc/xinetd.d",
            "/etc/host*",
            "/etc/resolv.conf",
            "/etc/network*",
            "/etc/NetworkManager/NetworkManager.conf",
            "/etc/NetworkManager/system-connections",
            "/etc/dnsmasq*",
            "/sys/class/net/*/flags"
        ])
        self.add_forbidden_path("/proc/net/rpc/use-gss-proxy")
        self.add_forbidden_path("/proc/net/rpc/*/channel")
        self.add_forbidden_path("/proc/net/rpc/*/flush")

        self.add_cmd_output("route -n", root_symlink="route")
        self.collect_iptable("filter")
        self.collect_iptable("nat")
        self.collect_iptable("mangle")
        self.add_cmd_output("netstat -neopa", root_symlink="netstat")
        self.add_cmd_outputs([
            "netstat -s",
            "netstat -agn",
            "ip route show table all",
            "ip -6 route show table all",
            "ip link",
            "ip address",
            "ifenslave -a",
            "ip mroute show",
            "ip maddr show",
            "ip neigh show",
            "nmcli general status",
            "nmcli connection show",
            "nmcli device status",
            "biosdevname -d"
        ])
        ip_link_result = self.call_ext_prog("ip -o link")
        if ip_link_result['status'] == 0:
            for eth in self.get_eth_interfaces(ip_link_result['output']):
                self.add_cmd_outputs([
                    "ethtool "+eth,
                    "ethtool -i "+eth,
                    "ethtool -k "+eth,
                    "ethtool -S "+eth,
                    "ethtool -a "+eth,
                    "ethtool -c "+eth,
                    "ethtool -g "+eth
                ])

        brctl_file = self.get_cmd_output_now("brctl show")
        if brctl_file:
            for br_name in self.get_bridge_name(brctl_file):
                self.add_cmd_output("brctl showstp "+br_name)

        nmcli_con_show_result = self.call_ext_prog(
            "nmcli --terse --fields NAME con show")
        if nmcli_con_show_result:
            for con in nmcli_con_show_result['output'].splitlines():
                self.add_cmd_output("nmcli connection show "+con)

        nmcli_dev_status_result = self.call_ext_prog(
            "nmcli --terse --fields DEVICE dev status")
        if nmcli_dev_status_result:
            for dev in nmcli_dev_status_result['output'].splitlines():
                self.add_cmd_output("nmcli device show "+dev)

        if self.get_option("traceroute"):
            self.add_cmd_output("/bin/traceroute -n %s" % self.trace_host)

        return

    def postproc(self):
        for root, dirs, files in os.walk(
                "/etc/NetworkManager/system-connections"):
            for net_conf in files:
                self.do_file_sub(
                    "/etc/NetworkManager/system-connections/"+net_conf,
                    r"psk=(.*)", r"psk=***")


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
            "/etc/network/interfaces",
            "/etc/network/interfaces.d",
            "/etc/ufw",
            "/var/log/ufw.Log",
            "/etc/resolv.conf"
        ])
        self.add_cmd_outputs([
            "/usr/sbin/ufw status",
            "/usr/sbin/ufw app list"
        ])
        if self.get_option("traceroute"):
            self.add_cmd_output("/usr/sbin/traceroute -n %s" % self.trace_host)


# vim: et ts=4 sw=4
