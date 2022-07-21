# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, UbuntuPlugin,
                                DebianPlugin, SoSPredicate, PluginOpt)


class Networking(Plugin):

    short_desc = 'Network and networking devices configuration'

    plugin_name = "networking"
    profiles = ('network', 'hardware', 'system')
    trace_host = "www.example.com"

    option_list = [
        PluginOpt("traceroute", default=False,
                  desc="collect a traceroute to %s" % trace_host),
        PluginOpt("namespace_pattern", default="", val_type=str,
                  desc=("Specific namespace names or patterns to collect, "
                        "whitespace delimited.")),
        PluginOpt("namespaces", default=None, val_type=int,
                  desc="Number of namespaces to collect, 0 for unlimited"),
        PluginOpt("ethtool_namespaces", default=True,
                  desc=("Toggle if ethtool commands should be run for each "
                        "namespace")),
        PluginOpt("eepromdump", default=False,
                  desc="Toggle collection of 'ethtool -e' for NICs")
    ]

    # switch to enable netstat "wide" (non-truncated) output mode
    ns_wide = "-W"

    # list of ethtool short options, used in add_copy_spec and add_cmd_tags
    # do NOT add there "e" (see eepromdump plugopt)
    ethtool_shortopts = "acdgiklmPST"

    def setup(self):
        super(Networking, self).setup()
        for opt in self.ethtool_shortopts:
            self.add_cmd_tags({
                'ethtool -%s .*' % opt: 'ethool_%s' % opt
            })

        self.add_file_tags({
            '/proc/net/bonding/bond.*': 'bond',
            '/etc/hosts': 'hosts'
        })

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

        self.add_cmd_output("ip -o addr", root_symlink="ip_addr",
                            tags='ip_addr')
        self.add_cmd_output("route -n", root_symlink="route", tags='route')
        self.add_cmd_output("plotnetcfg")

        self.add_cmd_output("netstat %s -neopa" % self.ns_wide,
                            root_symlink="netstat")

        self.add_cmd_output([
            "nstat -zas",
            "netstat -s",
            "netstat %s -agn" % self.ns_wide,
            "networkctl status -a",
            "ip route show table all",
            "ip -6 route show table all",
            "ip -d route show cache",
            "ip -d -6 route show cache",
            "ip -4 rule list",
            "ip -6 rule list",
            "ip vrf show",
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

        if self.path_isdir('/sys/class/devlink'):
            self.add_cmd_output([
                "devlink dev param show",
                "devlink dev info",
                "devlink port show",
            ])

            devlinks = self.collect_cmd_output("devlink dev")
            if devlinks['status'] == 0:
                devlinks_list = devlinks['output'].splitlines()
                for devlink in devlinks_list:
                    self.add_cmd_output("devlink dev eswitch show %s" %
                                        devlink)

        # below commands require some kernel module(s) to be loaded
        # run them only if the modules are loaded, or if explicitly requested
        # via --allow-system-changes option
        ip_macsec_show_cmd = "ip -s macsec show"
        macsec_pred = SoSPredicate(self, kmods=['macsec'])
        self.add_cmd_output(ip_macsec_show_cmd, pred=macsec_pred, changes=True)

        ss_cmd = "ss -peaonmi"
        ss_pred = SoSPredicate(self, kmods=[
            'tcp_diag', 'udp_diag', 'inet_diag', 'unix_diag', 'netlink_diag',
            'af_packet_diag', 'xsk_diag'
        ], required={'kmods': 'all'})
        self.add_cmd_output(ss_cmd, pred=ss_pred, changes=True)

        # Get ethtool output for every device that does not exist in a
        # namespace.
        _ecmds = ["ethtool -%s" % opt for opt in self.ethtool_shortopts]
        self.add_device_cmd([
            _cmd + " %(dev)s" for _cmd in _ecmds
        ], devices='ethernet')

        self.add_device_cmd([
            "ethtool %(dev)s",
            "ethtool --phy-statistics %(dev)s",
            "ethtool --show-priv-flags %(dev)s",
            "ethtool --show-eee %(dev)s",
            "tc -s filter show dev %(dev)s",
            "tc -s filter show dev %(dev)s ingress",
        ], devices="ethernet")

        # skip EEPROM collection by default, as it might hang or
        # negatively impact the system on some device types
        if self.get_option("eepromdump"):
            cmd = "ethtool -e %(dev)s"
            self._log_warn("WARNING: collecting an eeprom dump is known to "
                           "cause certain NIC drivers (e.g. bnx2x/tg3) to "
                           "interrupt device operation")
            self.add_device_cmd(cmd, devices="ethernet")

        # Collect information about bridges (some data already collected via
        # "ip .." commands)
        self.add_cmd_output([
            "bridge -s -s -d link show",
            "bridge -s -s -d -t fdb show",
            "bridge -s -s -d -t mdb show",
            "bridge -d vlan show"
        ])

        if self.get_option("traceroute"):
            self.add_cmd_output("/bin/traceroute -n %s" % self.trace_host,
                                priority=100)

        # Capture additional data from namespaces; each command is run
        # per-namespace.
        self.add_cmd_output("ip netns")
        cmd_prefix = "ip netns exec "
        namespaces = self.get_network_namespaces(
                self.get_option("namespace_pattern"),
                self.get_option("namespaces"))
        if (namespaces):
            # 'ip netns exec <foo> iptables-save' must be guarded by nf_tables
            # kmod, if 'iptables -V' output contains 'nf_tables'
            # analogously for ip6tables
            co = {'cmd': 'iptables -V', 'output': 'nf_tables'}
            co6 = {'cmd': 'ip6tables -V', 'output': 'nf_tables'}
            iptables_with_nft = (SoSPredicate(self, kmods=['nf_tables'])
                                 if self.test_predicate(self,
                                 pred=SoSPredicate(self, cmd_outputs=co))
                                 else None)
            ip6tables_with_nft = (SoSPredicate(self, kmods=['nf_tables'])
                                  if self.test_predicate(self,
                                  pred=SoSPredicate(self, cmd_outputs=co6))
                                  else None)
        for namespace in namespaces:
            _devs = self.devices['namespaced_network'][namespace]
            _subdir = "namespaces/%s" % namespace
            ns_cmd_prefix = cmd_prefix + namespace + " "
            self.add_cmd_output([
                ns_cmd_prefix + "ip -d address show",
                ns_cmd_prefix + "ip route show table all",
                ns_cmd_prefix + "ip -s -s neigh show",
                ns_cmd_prefix + "ip -4 rule list",
                ns_cmd_prefix + "ip -6 rule list",
                ns_cmd_prefix + "ip vrf show",
                ns_cmd_prefix + "netstat %s -neopa" % self.ns_wide,
                ns_cmd_prefix + "netstat -s",
                ns_cmd_prefix + "netstat %s -agn" % self.ns_wide,
                ns_cmd_prefix + "nstat -zas",
            ], priority=50, subdir=_subdir)
            self.add_cmd_output([ns_cmd_prefix + "iptables-save"],
                                pred=iptables_with_nft,
                                subdir=_subdir,
                                priority=50)
            self.add_cmd_output([ns_cmd_prefix + "ip6tables-save"],
                                pred=ip6tables_with_nft,
                                subdir=_subdir,
                                priority=50)

            ss_cmd = ns_cmd_prefix + "ss -peaonmi"
            # --allow-system-changes is handled directly in predicate
            # evaluation, so plugin code does not need to separately
            # check for it
            self.add_cmd_output(ss_cmd, pred=ss_pred, subdir=_subdir)

            # Collect ethtool commands only when ethtool_namespaces
            # is set to true.
            if self.get_option("ethtool_namespaces"):
                # Devices that exist in a namespace use less ethtool
                # parameters. Run this per namespace.
                self.add_device_cmd([
                    ns_cmd_prefix + "ethtool %(dev)s",
                    ns_cmd_prefix + "ethtool -i %(dev)s",
                    ns_cmd_prefix + "ethtool -k %(dev)s",
                    ns_cmd_prefix + "ethtool -S %(dev)s"
                ], devices=_devs['ethernet'], priority=50, subdir=_subdir)


class RedHatNetworking(Networking, RedHatPlugin):
    trace_host = "rhn.redhat.com"

    def setup(self):
        # Handle change from -T to -W in Red Hat netstat 2.0 and greater.
        try:
            netstat_pkg = self.policy.package_manager.packages['net-tools']
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
            "/etc/resolv.conf",
            "/run/netplan/*.yaml",
            "/etc/netplan/*.yaml",
            "/lib/netplan/*.yaml",
            "/run/systemd/network"
        ])

        if self.get_option("traceroute"):
            self.add_cmd_output("/usr/sbin/traceroute -n %s" % self.trace_host,
                                priority=100)


# vim: set et ts=4 sw=4 :
