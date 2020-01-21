# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import (Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin,
                         SoSPredicate)
from os import listdir
from re import match


class Networking(Plugin):
    """network and device configuration
    """
    plugin_name = "networking"
    profiles = ('network', 'hardware', 'system')
    trace_host = "www.example.com"
    option_list = [
        ("traceroute", "collect a traceroute to %s" % trace_host, "slow",
         False),
        ("namespace_regex", "Specific namespaces regex to be " +
         "collected, namespaces regex should be separated by whitespace " +
         "as for example \"eth* ens2\"", "fast", ""),
        ("namespaces", "Number of namespaces to collect, 0 for unlimited. " +
         "Incompatible with the namespace_regex plugin option", "slow", 0),
        ("ethtool_namespaces", "Define if ethtool commands should be " +
         "collected for namespaces", "slow", True)
    ]

    # switch to enable netstat "wide" (non-truncated) output mode
    ns_wide = "-W"

    def collect_iptable(self, tablename):
        """ When running the iptables command, it unfortunately auto-loads
        the modules before trying to get output.  Some people explicitly
        don't want this, so check if the modules are loaded before running
        the command.  If they aren't loaded, there can't possibly be any
        relevant rules in that table """

        modname = "iptable_" + tablename
        cmd = "iptables -t " + tablename + " -nvL"
        self.add_cmd_output(cmd, pred=SoSPredicate(self, kmods=[modname]))

    def collect_ip6table(self, tablename):
        """ Same as function above, but for ipv6 """

        modname = "ip6table_" + tablename
        cmd = "ip6tables -t " + tablename + " -nvL"
        self.add_cmd_output(cmd, pred=SoSPredicate(self, kmods=[modname]))

    def collect_nftables(self):
        """ Collects nftables rulesets with 'nft' commands if the modules
        are present """

        self.add_cmd_output(
            "nft list ruleset",
            pred=SoSPredicate(self, kmods=['nf_tables'])
        )

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
            "/sys/class/net/*/device/numa_node",
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
        ])

        # below commands require some kernel module(s) to be loaded
        # run them only if the modules are loaded, or if explicitly requested
        # via --allow-system-changes option
        ip_macsec_show_cmd = "ip -s macsec show"
        macsec_pred = SoSPredicate(self, kmods=['macsec'])
        self.add_cmd_output(ip_macsec_show_cmd, pred=macsec_pred, changes=True)

        ss_cmd = "ss -peaonmi"
        ss_pred = SoSPredicate(self, kmods=[
            'tcp_diag', 'udp_diag', 'inet_diag', 'unix_diag', 'netlink_diag',
            'af_packet_diag'
        ], required={'kmods': 'all'})
        self.add_cmd_output(ss_cmd, pred=ss_pred, changes=True)

        # When iptables is called it will load the modules
        # iptables and iptables_filter if they are not loaded.
        # The same goes for ipv6.
        self.add_cmd_output(
            "iptables -vnxL",
            pred=SoSPredicate(self, kmods=['iptable_filter'])
        )

        self.add_cmd_output(
            "ip6tables -vnxL",
            pred=SoSPredicate(self, kmods=['ip6table_filter'])
        )

        # Get ethtool output for every device that does not exist in a
        # namespace.
        for eth in listdir("/sys/class/net/"):
            # skip 'bonding_masters' file created when loading the bonding
            # module but the file does not correspond to a device
            if eth == "bonding_masters":
                continue
            self.add_cmd_output([
                "ethtool " + eth,
                "ethtool -d " + eth,
                "ethtool -i " + eth,
                "ethtool -k " + eth,
                "ethtool -S " + eth,
                "ethtool -T " + eth,
                "ethtool -a " + eth,
                "ethtool -c " + eth,
                "ethtool -g " + eth,
                "ethtool -e " + eth,
                "ethtool -P " + eth,
                "ethtool -l " + eth,
                "ethtool --phy-statistics " + eth,
                "ethtool --show-priv-flags " + eth,
                "ethtool --show-eee " + eth
            ])

        # Collect information about bridges (some data already collected via
        # "ip .." commands)
        self.add_cmd_output([
            "bridge -s -s -d link show",
            "bridge -s -s -d -t fdb show",
            "bridge -s -s -d -t mdb show",
            "bridge -d vlan show"
        ])

        if self.get_option("traceroute"):
            self.add_cmd_output("/bin/traceroute -n %s" % self.trace_host)

        # Capture additional data from namespaces; each command is run
        # per-namespace.
        ip_netns = self.collect_cmd_output("ip netns")
        cmd_prefix = "ip netns exec "
        if ip_netns['status'] == 0:
            out_ns = []
            # Regex initialization outside of for loop
            if self.get_option("namespace_regex"):
                regex = '(?:%s)' % '|'.join(
                        self.get_option("namespace_regex").split())
            for line in ip_netns['output'].splitlines():
                # If there's no namespaces, no need to continue
                if line.startswith("Object \"netns\" is unknown") \
                        or line.isspace() \
                        or line[:1].isspace():
                    continue
                # if namespace_regex defined, append only namespaces
                # matching with regex
                if self.get_option("namespace_regex"):
                    if bool(match(regex, line)):
                        out_ns.append(line.partition(' ')[0])

                # if namespaces is defined and namespace_regex is not defined
                # remove from out_ns namespaces with higher index than defined
                elif self.get_option("namespaces") != 0:
                    out_ns.append(line.partition(' ')[0])
                    if len(out_ns) == self.get_option("namespaces"):
                        self._log_warn("Limiting namespace iteration " +
                                       "to first %s namespaces found"
                                       % self.get_option("namespaces"))
                        break
                else:
                    out_ns.append(line.partition(' ')[0])

            for namespace in out_ns:
                ns_cmd_prefix = cmd_prefix + namespace + " "
                self.add_cmd_output([
                    ns_cmd_prefix + "ip address show",
                    ns_cmd_prefix + "ip route show table all",
                    ns_cmd_prefix + "iptables-save",
                    ns_cmd_prefix + "netstat %s -neopa" % self.ns_wide,
                    ns_cmd_prefix + "netstat -s",
                    ns_cmd_prefix + "netstat %s -agn" % self.ns_wide,
                ])

                ss_cmd = ns_cmd_prefix + "ss -peaonmi"
                # --allow-system-changes is handled directly in predicate
                # evaluation, so plugin code does not need to separately
                # check for it
                self.add_cmd_output(ss_cmd, pred=ss_pred)

            # Collect ethtool commands only when ethtool_namespaces
            # is set to true.
            if self.get_option("ethtool_namespaces"):
                # Devices that exist in a namespace use less ethtool
                # parameters. Run this per namespace.
                for namespace in out_ns:
                    ns_cmd_prefix = cmd_prefix + namespace + " "
                    netns_netdev_list = self.exec_cmd(
                        ns_cmd_prefix + "ls -1 /sys/class/net/"
                    )
                    for eth in netns_netdev_list['output'].splitlines():
                        # skip 'bonding_masters' file created when loading the
                        # bonding module but the file does not correspond to
                        # a device
                        if eth == "bonding_masters":
                            continue
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
