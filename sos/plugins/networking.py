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

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
import os
import re


class Networking(Plugin):
    """network and device configuration
    """
    plugin_name = "networking"
    profiles = ('network', 'hardware', 'system')
    trace_host = "www.example.com"
    option_list = [(
        ("traceroute", "collect a traceroute to %s" % trace_host, "slow",
         False)
    )]

    # switch to enable netstat "wide" (non-truncated) output mode
    ns_wide = "-W"

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

    def get_ip_netns(self, ip_netns_file):
        """Returns a list for which items are namespaces in the output of
        ip netns stored in the ip_netns_file.
        """
        out = []
        try:
            ip_netns_out = open(ip_netns_file).read()
        except:
            return out
        for line in ip_netns_out.splitlines():
            # If there's no namespaces, no need to continue
            if line.startswith("Object \"netns\" is unknown") \
               or line.isspace() \
               or line[:1].isspace():
                return out
            out.append(line)
        return out

    def get_netns_devs(self, namespace):
        """Returns a list for which items are devices that exist within
        the provided namespace.
        """
        ip_link_result = self.call_ext_prog("ip netns exec " + namespace +
                                            " ip -o link")
        dev_list = []
        if ip_link_result['status'] == 0:
            for eth in self.get_eth_interfaces(ip_link_result['output']):
                dev = eth.replace('@NONE', '')
                dev_list.append(dev)
        return dev_list

    def collect_iptable(self, tablename):
        """ When running the iptables command, it unfortunately auto-loads
        the modules before trying to get output.  Some people explicitly
        don't want this, so check if the modules are loaded before running
        the command.  If they aren't loaded, there can't possibly be any
        relevant rules in that table """

        modname = "iptable_"+tablename
        if self.check_ext_prog("grep -q %s /proc/modules" % modname):
            cmd = "iptables -t "+tablename+" -nvL"
            self.add_cmd_output(cmd)

    def collect_ip6table(self, tablename):
        """ Same as function above, but for ipv6 """

        modname = "ip6table_"+tablename
        if self.check_ext_prog("grep -q %s /proc/modules" % modname):
            cmd = "ip6tables -t "+tablename+" -nvL"
            self.add_cmd_output(cmd)

    def setup(self):
        super(Networking, self).setup()
        self.add_copy_spec([
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
            "/sys/class/net/*/flags",
            "/etc/iproute2"
        ])
        self.add_forbidden_path("/proc/net/rpc/use-gss-proxy")
        self.add_forbidden_path("/proc/net/rpc/*/channel")
        self.add_forbidden_path("/proc/net/rpc/*/flush")
        # Cisco CDP
        self.add_forbidden_path("/proc/net/cdp")
        self.add_forbidden_path("/sys/net/cdp")

        self.add_cmd_output("ip -o addr", root_symlink="ip_addr")
        self.add_cmd_output("route -n", root_symlink="route")
        self.add_cmd_output("plotnetcfg")
        self.collect_iptable("filter")
        self.collect_iptable("nat")
        self.collect_iptable("mangle")
        self.collect_ip6table("filter")
        self.collect_ip6table("nat")
        self.collect_ip6table("mangle")

        self.add_cmd_output("netstat %s -neopa" % self.ns_wide,
                            root_symlink="netstat")

        self.add_cmd_output([
            "netstat -s",
            "netstat %s -agn" % self.ns_wide,
            "ip route show table all",
            "ip -6 route show table all",
            "ip -4 rule",
            "ip -6 rule",
            "ip -s link",
            "ip address",
            "ifenslave -a",
            "ip mroute show",
            "ip maddr show",
            "ip neigh show",
            "ip neigh show nud noarp",
            "biosdevname -d",
            "tc -s qdisc show",
            "iptables -vnxL",
            "ip6tables -vnxL"
        ])

        # There are some incompatible changes in nmcli since
        # the release of NetworkManager >= 0.9.9. In addition,
        # NetworkManager >= 0.9.9 will use the long names of
        # "nmcli" objects.

        # All versions conform to the following templates with differnt
        # strings for the object being operated on.
        nmcli_con_details_template = "nmcli con %s id"
        nmcli_dev_details_template = "nmcli dev %s"

        # test NetworkManager status for the specified major version
        def test_nm_status(version=1):
            status_template = "nmcli --terse --fields RUNNING %s status"
            obj_table = [
                "nm",        # <  0.9.9
                "general"    # >= 0.9.9
            ]
            status = self.call_ext_prog(status_template % obj_table[version])
            return status['output'].lower().startswith("running")

        # NetworkManager >= 0.9.9 (Use short name of objects for nmcli)
        if test_nm_status(version=1):
            self.add_cmd_output([
                "nmcli general status",
                "nmcli con",
                "nmcli con show --active",
                "nmcli dev"])
            nmcli_con_details_cmd = nmcli_con_details_template % "show"
            nmcli_dev_details_cmd = nmcli_dev_details_template % "show"

        # NetworkManager < 0.9.9 (Use short name of objects for nmcli)
        elif test_nm_status(version=0):
            self.add_cmd_output([
                "nmcli nm status",
                "nmcli con",
                "nmcli con status",
                "nmcli dev"])
            nmcli_con_details_cmd = nmcli_con_details_template % "list id"
            nmcli_dev_details_cmd = nmcli_dev_details_template % "list iface"

        # No grokkable NetworkManager version present
        else:
            nmcli_con_details_cmd = ""
            nmcli_dev_details_cmd = ""

        if len(nmcli_con_details_cmd) > 0:
            nmcli_con_show_result = self.call_ext_prog(
                "nmcli --terse --fields NAME con")
            if nmcli_con_show_result['status'] == 0:
                for con in nmcli_con_show_result['output'].splitlines():
                    if con[0:7] == 'Warning':
                        continue
                    self.add_cmd_output("%s '%s'" %
                                        (nmcli_con_details_cmd, con))

            nmcli_dev_status_result = self.call_ext_prog(
                "nmcli --terse --fields DEVICE dev")
            if nmcli_dev_status_result['status'] == 0:
                for dev in nmcli_dev_status_result['output'].splitlines():
                    if dev[0:7] == 'Warning':
                        continue
                    self.add_cmd_output("%s '%s'" %
                                        (nmcli_dev_details_cmd, dev))

        # Get ethtool output for every device that does not exist in a
        # namespace.
        ip_link_result = self.call_ext_prog("ip -o link")
        if ip_link_result['status'] == 0:
            for dev in self.get_eth_interfaces(ip_link_result['output']):
                eth = dev.replace('@NONE', '')
                self.add_cmd_output([
                    "ethtool "+eth,
                    "ethtool -d "+eth,
                    "ethtool -i "+eth,
                    "ethtool -k "+eth,
                    "ethtool -S "+eth,
                    "ethtool -T "+eth,
                    "ethtool -a "+eth,
                    "ethtool -c "+eth,
                    "ethtool -g "+eth
                ])

        # brctl command will load bridge and related kernel modules
        # if those modules are not loaded at the time of brctl command running
        # This behaviour causes an unexpected configuration change for system.
        # sosreport should aovid such situation.
        if self.is_module_loaded("bridge"):
            brctl_file = self.get_cmd_output_now("brctl show")
            if brctl_file:
                for br_name in self.get_bridge_name(brctl_file):
                    self.add_cmd_output([
                            "brctl showstp "+br_name,
                            "brctl showmacs "+br_name
                    ])

        if self.get_option("traceroute"):
            self.add_cmd_output("/bin/traceroute -n %s" % self.trace_host)

        # Capture additional data from namespaces; each command is run
        # per-namespace.
        ip_netns_file = self.get_cmd_output_now("ip netns")
        cmd_prefix = "ip netns exec "
        if ip_netns_file:
            for namespace in self.get_ip_netns(ip_netns_file):
                self.add_cmd_output([
                    cmd_prefix + namespace + " ip address show",
                    cmd_prefix + namespace + " ip route show table all",
                    cmd_prefix + namespace + " iptables-save"
                ])

            # Devices that exist in a namespace use less ethtool
            # parameters. Run this per namespace.
            for namespace in self.get_ip_netns(ip_netns_file):
                for eth in self.get_netns_devs(namespace):
                    ns_cmd_prefix = cmd_prefix + namespace + " "
                    self.add_cmd_output([
                        ns_cmd_prefix + "ethtool " + eth,
                        ns_cmd_prefix + "ethtool -i " + eth,
                        ns_cmd_prefix + "ethtool -k " + eth,
                        ns_cmd_prefix + "ethtool -S " + eth
                    ])

        return

    def postproc(self):
        for root, dirs, files in os.walk(
                "/etc/NetworkManager/system-connections"):
            for net_conf in files:
                self.do_file_sub(
                    "/etc/NetworkManager/system-connections/"+net_conf,
                    r"psk=(.*)", r"psk=***")


class RedHatNetworking(Networking, RedHatPlugin):
    trace_host = "rhn.redhat.com"

    def setup(self):
        # Handle change from -T to -W in Red Hat netstat 2.0 and greater.
        netstat_pkg = self.policy().package_manager.all_pkgs()['net-tools']
        try:
            # major version
            if int(netstat_pkg['version'][0]) < 2:
                self.ns_wide = "-T"
        except:
            # default to upstream option
            pass

        super(RedHatNetworking, self).setup()


class UbuntuNetworking(Networking, UbuntuPlugin, DebianPlugin):
    trace_host = "archive.ubuntu.com"

    def setup(self):
        super(UbuntuNetworking, self).setup()

        self.add_copy_spec([
            "/etc/resolvconf",
            "/etc/network/interfaces",
            "/etc/network/interfaces.d",
            "/etc/ufw",
            "/var/log/ufw.Log",
            "/etc/resolv.conf"
        ])
        self.add_cmd_output([
            "/usr/sbin/ufw status",
            "/usr/sbin/ufw app list"
        ])
        if self.get_option("traceroute"):
            self.add_cmd_output("/usr/sbin/traceroute -n %s" % self.trace_host)


# vim: set et ts=4 sw=4 :
