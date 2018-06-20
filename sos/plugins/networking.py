# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
        except IOError:
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
        except IOError:
            return out
        for line in ip_netns_out.splitlines():
            # If there's no namespaces, no need to continue
            if line.startswith("Object \"netns\" is unknown") \
               or line.isspace() \
               or line[:1].isspace():
                return out
            out.append(line.partition(' ')[0])
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

    def collect_nftables(self):
        """ Collects nftables rulesets with 'nft' commands if the modules
        are present """

        if self.check_ext_prog("grep -q nf_tables /proc/modules"):
            self.add_cmd_output("nft list ruleset")

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
            "/etc/nftables",
            "/etc/sysconfig/nftables.conf",
            "/etc/nftables.conf",
            "/etc/dnsmasq*",
            "/sys/class/net/*/flags",
            "/sys/class/net/*/statistics/",
            "/etc/iproute2"
        ])

        self.add_forbidden_path([
            "/proc/net/rpc/use-gss-proxy",
            "/proc/net/rpc/*/channel",
            "/proc/net/rpc/*/flush",
            # Cisco CDP
            "/proc/net/cdp",
            "/sys/net/cdp",
            # Dialogic Diva
            "/proc/net/eicon"
        ])

        self.add_cmd_output("ip -o addr", root_symlink="ip_addr")
        self.add_cmd_output("route -n", root_symlink="route")
        self.add_cmd_output("plotnetcfg")
        # collect iptables -t for any existing table, if we can't read the
        # tables, collect 3 default ones (nat, mangle, filter)
        try:
            ip_tables_names = open("/proc/net/ip_tables_names").read()
        except IOError:
            ip_tables_names = "nat\nmangle\nfilter\n"
        for table in ip_tables_names.splitlines():
            self.collect_iptable(table)
        # collect the same for ip6tables
        try:
            ip_tables_names = open("/proc/net/ip6_tables_names").read()
        except IOError:
            ip_tables_names = "nat\nmangle\nfilter\n"
        for table in ip_tables_names.splitlines():
            self.collect_ip6table(table)

        self.collect_nftables()

        self.add_cmd_output("netstat %s -neopa" % self.ns_wide,
                            root_symlink="netstat")

        self.add_cmd_output([
            "netstat -s",
            "netstat %s -agn" % self.ns_wide,
            "ss -peaonmi",
            "ip route show table all",
            "ip -6 route show table all",
            "ip -4 rule",
            "ip -6 rule",
            "ip -s -d link",
            "ip -d address",
            "ifenslave -a",
            "ip mroute show",
            "ip maddr show",
            "ip -s -s neigh show",
            "ip neigh show nud noarp",
            "biosdevname -d",
            "tc -s qdisc show",
            "ip -s macsec show",
        ])

        # When iptables is called it will load the modules
        # iptables and iptables_filter if they are not loaded.
        # The same goes for ipv6.
        if self.check_ext_prog("grep -q iptable_filter /proc/modules"):
            self.add_cmd_output("iptables -vnxL")
        if self.check_ext_prog("grep -q ip6table_filter /proc/modules"):
            self.add_cmd_output("ip6tables -vnxL")

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
                ns_cmd_prefix = cmd_prefix + namespace + " "
                self.add_cmd_output([
                    ns_cmd_prefix + "ip address show",
                    ns_cmd_prefix + "ip route show table all",
                    ns_cmd_prefix + "iptables-save",
                    ns_cmd_prefix + "ss -peaonmi",
                    ns_cmd_prefix + "netstat %s -neopa" % self.ns_wide,
                    ns_cmd_prefix + "netstat -s",
                    ns_cmd_prefix + "netstat %s -agn" % self.ns_wide
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


class RedHatNetworking(Networking, RedHatPlugin):
    trace_host = "rhn.redhat.com"

    def setup(self):
        # Handle change from -T to -W in Red Hat netstat 2.0 and greater.
        try:
            netstat_pkg = self.policy.package_manager.all_pkgs()['net-tools']
            # major version
            if int(netstat_pkg['version'][0]) < 2:
                self.ns_wide = "-T"
        except Exception:
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
            "/etc/resolv.conf",
            "/run/netplan/*.yaml",
            "/etc/netplan/*.yaml",
            "/lib/netplan/*.yaml",
            "/run/systemd/network"
        ])
        self.add_cmd_output([
            "/usr/sbin/ufw status",
            "/usr/sbin/ufw app list"
        ])
        if self.get_option("traceroute"):
            self.add_cmd_output("/usr/sbin/traceroute -n %s" % self.trace_host)


# vim: set et ts=4 sw=4 :
